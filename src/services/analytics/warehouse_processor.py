"""Data warehouse and analytics processing for Track F3.

Handles activation funnel, adherence tracking, retention analysis, and revenue metrics.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

try:
    from ...models.analytics import (
        EventType,
        BaseEvent,
        UserProfile,
        CohortMetrics,
        FunnelMetrics,
        RevenueMetrics,
        ConsentType
    )
except ImportError:
    # Fallback for direct imports
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from models.analytics import (
        EventType,
        BaseEvent,
        UserProfile,
        CohortMetrics,
        FunnelMetrics,
        RevenueMetrics,
        ConsentType
    )

logger = logging.getLogger(__name__)


class WarehouseProcessor:
    """Data warehouse processing for analytics dashboards."""
    
    def __init__(self, analytics_service):
        self.analytics_service = analytics_service
        
        # Processed metrics cache
        self.funnel_metrics_cache: Dict[str, FunnelMetrics] = {}
        self.cohort_metrics_cache: Dict[str, CohortMetrics] = {}
        self.revenue_metrics_cache: Dict[str, RevenueMetrics] = {}
        
        # Cache TTL
        self.cache_ttl_hours = 1
        
        # Processing configuration
        self.cohort_analysis_days = [1, 7, 30, 90]
        self.funnel_steps = [
            EventType.USER_REGISTERED,
            EventType.ONBOARDING_COMPLETED,
            EventType.PLAN_GENERATED,
            EventType.MEAL_LOGGED,
            # 7-day and 30-day activity are calculated differently
        ]
    
    async def process_activation_funnel(
        self,
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> FunnelMetrics:
        """Calculate activation funnel metrics."""
        cache_key = f"funnel_{start_date.date()}_{end_date.date()}"
        
        # Check cache
        if not force_refresh and cache_key in self.funnel_metrics_cache:
            cached = self.funnel_metrics_cache[cache_key]
            if (datetime.now(timezone.utc) - cached.period_end).total_seconds() < self.cache_ttl_hours * 3600:
                return cached
        
        try:
            # Get all events in period
            events = [
                e for e in self.analytics_service.events
                if start_date <= e.timestamp <= end_date
            ]
            
            # Group events by user
            user_events = defaultdict(list)
            for event in events:
                if event.user_id:
                    user_events[event.user_id].append(event)
            
            # Calculate funnel steps
            registered_users = set()
            completed_onboarding = set()
            generated_first_plan = set()
            logged_first_meal = set()
            active_day_7 = set()
            active_day_30 = set()
            
            for user_id, user_event_list in user_events.items():
                user_event_types = {e.event_type for e in user_event_list}
                user_timestamps = {e.event_type: e.timestamp for e in user_event_list}
                
                # Registration (implied by having any events)
                registered_users.add(user_id)
                
                # Onboarding completion
                if EventType.ONBOARDING_COMPLETED in user_event_types:
                    completed_onboarding.add(user_id)
                
                # First plan generation
                if EventType.PLAN_GENERATED in user_event_types:
                    generated_first_plan.add(user_id)
                
                # First meal logged
                if EventType.MEAL_LOGGED in user_event_types:
                    logged_first_meal.add(user_id)
                
                # 7-day activity (check if user was active within 7 days of registration)
                first_event_time = min(e.timestamp for e in user_event_list)
                seven_day_cutoff = first_event_time + timedelta(days=7)
                recent_events = [e for e in user_event_list if e.timestamp <= seven_day_cutoff]
                if len(recent_events) >= 3:  # Active = 3+ events in first 7 days
                    active_day_7.add(user_id)
                
                # 30-day activity
                thirty_day_cutoff = first_event_time + timedelta(days=30)
                if thirty_day_cutoff <= datetime.now(timezone.utc):
                    recent_events_30 = [e for e in user_event_list if e.timestamp <= thirty_day_cutoff]
                    if len(recent_events_30) >= 5:  # Active = 5+ events in first 30 days
                        active_day_30.add(user_id)
            
            # Calculate conversion rates
            total_registered = len(registered_users)
            
            funnel_metrics = FunnelMetrics(
                period_start=start_date,
                period_end=end_date,
                registered_users=total_registered,
                completed_onboarding=len(completed_onboarding),
                generated_first_plan=len(generated_first_plan),
                logged_first_meal=len(logged_first_meal),
                active_day_7=len(active_day_7),
                active_day_30=len(active_day_30),
                
                # Conversion rates
                onboarding_rate=len(completed_onboarding) / max(total_registered, 1),
                first_plan_rate=len(generated_first_plan) / max(total_registered, 1),
                first_meal_rate=len(logged_first_meal) / max(total_registered, 1),
                d7_activation_rate=len(active_day_7) / max(total_registered, 1),
                d30_retention_rate=len(active_day_30) / max(total_registered, 1)
            )
            
            # Cache result
            self.funnel_metrics_cache[cache_key] = funnel_metrics
            
            logger.info(f"Processed activation funnel: {total_registered} users, "
                       f"{funnel_metrics.d7_activation_rate:.2%} D7 activation")
            
            return funnel_metrics
        
        except Exception as e:
            logger.error(f"Error processing activation funnel: {e}")
            raise
    
    async def process_cohort_analysis(
        self,
        cohort_month: str,  # YYYY-MM format
        force_refresh: bool = False
    ) -> CohortMetrics:
        """Calculate cohort retention and engagement metrics."""
        cache_key = f"cohort_{cohort_month}"
        
        # Check cache
        if not force_refresh and cache_key in self.cohort_metrics_cache:
            cached = self.cohort_metrics_cache[cache_key]
            age_hours = (datetime.now(timezone.utc) - cached.calculated_at).total_seconds() / 3600
            if age_hours < self.cache_ttl_hours:
                return cached
        
        try:
            # Parse cohort month
            year, month = map(int, cohort_month.split('-'))
            cohort_start = datetime(year, month, 1, tzinfo=timezone.utc)
            
            # Calculate cohort end (next month)
            if month == 12:
                cohort_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                cohort_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
            
            # Find cohort users (users who registered in this month)
            cohort_users = set()
            registration_dates = {}
            
            for user_id, profile in self.analytics_service.user_profiles.items():
                if cohort_start <= profile.created_at < cohort_end:
                    cohort_users.add(user_id)
                    registration_dates[user_id] = profile.created_at
            
            cohort_size = len(cohort_users)
            if cohort_size == 0:
                # Return empty metrics for cohorts with no users
                return CohortMetrics(
                    cohort_id=cohort_month,
                    cohort_size=0,
                    day_1_retention=0.0,
                    day_7_retention=0.0,
                    day_30_retention=0.0,
                    day_90_retention=0.0,
                    avg_plans_per_user=0.0,
                    avg_meals_logged_per_user=0.0,
                    avg_adherence_percent=0.0,
                    conversion_rate=0.0,
                    avg_ltv_usd=0.0,
                    calculated_at=datetime.now(timezone.utc)
                )
            
            # Calculate retention for each time period
            retention_metrics = {}
            engagement_metrics = defaultdict(list)
            ltv_values = []
            converted_users = 0
            
            for user_id in cohort_users:
                reg_date = registration_dates[user_id]
                profile = self.analytics_service.user_profiles[user_id]
                
                # Check retention at each interval
                for days in self.cohort_analysis_days:
                    retention_cutoff = reg_date + timedelta(days=days)
                    
                    # Only calculate if enough time has passed
                    if retention_cutoff <= datetime.now(timezone.utc):
                        # Check if user was active after the cutoff
                        if profile.last_active_at and profile.last_active_at >= retention_cutoff:
                            retention_key = f"day_{days}_retention"
                            if retention_key not in retention_metrics:
                                retention_metrics[retention_key] = 0
                            retention_metrics[retention_key] += 1
                
                # Collect engagement metrics
                engagement_metrics['plans'].append(profile.total_plans_generated)
                engagement_metrics['meals'].append(profile.total_meals_logged)
                
                # Calculate adherence (meals logged / plans generated)
                if profile.total_plans_generated > 0:
                    adherence = min(profile.total_meals_logged / (profile.total_plans_generated * 7), 1.0)
                    engagement_metrics['adherence'].append(adherence * 100)
                
                # LTV and conversion
                ltv_values.append(profile.ltv_usd)
                if profile.current_tier and profile.current_tier != "free":
                    converted_users += 1
            
            # Calculate final metrics
            cohort_metrics = CohortMetrics(
                cohort_id=cohort_month,
                cohort_size=cohort_size,
                
                # Retention rates
                day_1_retention=retention_metrics.get("day_1_retention", 0) / cohort_size,
                day_7_retention=retention_metrics.get("day_7_retention", 0) / cohort_size,
                day_30_retention=retention_metrics.get("day_30_retention", 0) / cohort_size,
                day_90_retention=retention_metrics.get("day_90_retention", 0) / cohort_size,
                
                # Engagement metrics
                avg_plans_per_user=sum(engagement_metrics['plans']) / cohort_size,
                avg_meals_logged_per_user=sum(engagement_metrics['meals']) / cohort_size,
                avg_adherence_percent=sum(engagement_metrics['adherence']) / max(len(engagement_metrics['adherence']), 1),
                
                # Monetization metrics
                conversion_rate=converted_users / cohort_size,
                avg_ltv_usd=sum(ltv_values) / cohort_size,
                
                calculated_at=datetime.now(timezone.utc)
            )
            
            # Cache result
            self.cohort_metrics_cache[cache_key] = cohort_metrics
            
            logger.info(f"Processed cohort {cohort_month}: {cohort_size} users, "
                       f"{cohort_metrics.day_30_retention:.2%} D30 retention")
            
            return cohort_metrics
        
        except Exception as e:
            logger.error(f"Error processing cohort analysis: {e}")
            raise
    
    async def process_revenue_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> RevenueMetrics:
        """Calculate revenue and subscription metrics."""
        cache_key = f"revenue_{start_date.date()}_{end_date.date()}"
        
        # Check cache
        if not force_refresh and cache_key in self.revenue_metrics_cache:
            cached = self.revenue_metrics_cache[cache_key]
            age_hours = (datetime.now(timezone.utc) - end_date).total_seconds() / 3600
            if age_hours < self.cache_ttl_hours:
                return cached
        
        try:
            # Get subscription events in period
            subscription_events = [
                e for e in self.analytics_service.events
                if e.event_type in [EventType.SUBSCRIBE_ACTIVATED, EventType.CHURNED]
                and start_date <= e.timestamp <= end_date
            ]
            
            # Count subscription changes
            new_subscribers = 0
            churned_subscribers = 0
            subscription_revenue = 0.0
            
            for event in subscription_events:
                if event.event_type == EventType.SUBSCRIBE_ACTIVATED:
                    new_subscribers += 1
                    subscription_revenue += event.properties.get("price_usd", 0)
                elif event.event_type == EventType.CHURNED:
                    churned_subscribers += 1
            
            # Calculate current subscriber counts
            free_users = 0
            plus_subscribers = 0
            pro_subscribers = 0
            total_ltv = 0.0
            
            for profile in self.analytics_service.user_profiles.values():
                total_ltv += profile.ltv_usd
                
                if not profile.current_tier or profile.current_tier == "free":
                    free_users += 1
                elif profile.current_tier == "plus":
                    plus_subscribers += 1
                elif profile.current_tier == "pro":
                    pro_subscribers += 1
            
            total_active_subscribers = plus_subscribers + pro_subscribers
            total_users = free_users + total_active_subscribers
            
            # Calculate churn rates (simplified)
            voluntary_churn_events = [
                e for e in subscription_events
                if e.event_type == EventType.CHURNED 
                and e.properties.get("churn_type") == "voluntary"
            ]
            involuntary_churn_events = [
                e for e in subscription_events
                if e.event_type == EventType.CHURNED 
                and e.properties.get("churn_type") == "involuntary"
            ]
            
            # Calculate period length in months for MRR/ARR
            period_days = (end_date - start_date).days
            months_in_period = period_days / 30.44  # Average days per month
            
            # Estimate MRR (simplified calculation)
            monthly_revenue = subscription_revenue / max(months_in_period, 1)
            
            revenue_metrics = RevenueMetrics(
                period_start=start_date,
                period_end=end_date,
                
                # Subscription metrics
                new_subscribers=new_subscribers,
                churned_subscribers=churned_subscribers,
                net_subscriber_growth=new_subscribers - churned_subscribers,
                total_active_subscribers=total_active_subscribers,
                
                # Revenue metrics
                mrr_usd=monthly_revenue,
                arr_usd=monthly_revenue * 12,
                arpu_usd=total_ltv / max(total_users, 1),
                ltv_usd=total_ltv / max(total_active_subscribers, 1) if total_active_subscribers > 0 else 0,
                
                # Tier breakdown
                free_users=free_users,
                plus_subscribers=plus_subscribers,
                pro_subscribers=pro_subscribers,
                
                # Churn analysis
                voluntary_churn_rate=len(voluntary_churn_events) / max(total_active_subscribers, 1),
                involuntary_churn_rate=len(involuntary_churn_events) / max(total_active_subscribers, 1)
            )
            
            # Cache result
            self.revenue_metrics_cache[cache_key] = revenue_metrics
            
            logger.info(f"Processed revenue metrics: ${monthly_revenue:.2f} MRR, "
                       f"{total_active_subscribers} active subscribers")
            
            return revenue_metrics
        
        except Exception as e:
            logger.error(f"Error processing revenue metrics: {e}")
            raise
    
    # Dashboard data aggregation
    
    async def get_dashboard_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        try:
            # Process all metrics
            funnel_metrics = await self.process_activation_funnel(start_date, end_date)
            revenue_metrics = await self.process_revenue_metrics(start_date, end_date)
            
            # Get current month cohort
            current_cohort = end_date.strftime("%Y-%m")
            cohort_metrics = await self.process_cohort_analysis(current_cohort)
            
            # Get event summary
            event_counts = self.analytics_service.get_event_counts_by_type(start_date, end_date)
            
            # Calculate key metrics
            total_events = sum(event_counts.values())
            total_users = len(self.analytics_service.user_profiles)
            
            dashboard_data = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": (end_date - start_date).days
                },
                
                "overview": {
                    "total_events": total_events,
                    "total_users": total_users,
                    "active_subscribers": revenue_metrics.total_active_subscribers,
                    "mrr_usd": revenue_metrics.mrr_usd
                },
                
                "activation_funnel": {
                    "registered_users": funnel_metrics.registered_users,
                    "completed_onboarding": funnel_metrics.completed_onboarding,
                    "generated_first_plan": funnel_metrics.generated_first_plan,
                    "logged_first_meal": funnel_metrics.logged_first_meal,
                    "active_day_7": funnel_metrics.active_day_7,
                    "active_day_30": funnel_metrics.active_day_30,
                    
                    "conversion_rates": {
                        "onboarding": funnel_metrics.onboarding_rate,
                        "first_plan": funnel_metrics.first_plan_rate,
                        "first_meal": funnel_metrics.first_meal_rate,
                        "d7_activation": funnel_metrics.d7_activation_rate,
                        "d30_retention": funnel_metrics.d30_retention_rate
                    }
                },
                
                "engagement": {
                    "avg_plans_per_user": cohort_metrics.avg_plans_per_user,
                    "avg_meals_logged_per_user": cohort_metrics.avg_meals_logged_per_user,
                    "avg_adherence_percent": cohort_metrics.avg_adherence_percent,
                    
                    "retention": {
                        "day_1": cohort_metrics.day_1_retention,
                        "day_7": cohort_metrics.day_7_retention,
                        "day_30": cohort_metrics.day_30_retention,
                        "day_90": cohort_metrics.day_90_retention
                    }
                },
                
                "monetization": {
                    "revenue": {
                        "mrr_usd": revenue_metrics.mrr_usd,
                        "arr_usd": revenue_metrics.arr_usd,
                        "arpu_usd": revenue_metrics.arpu_usd,
                        "ltv_usd": revenue_metrics.ltv_usd
                    },
                    
                    "subscribers": {
                        "free": revenue_metrics.free_users,
                        "plus": revenue_metrics.plus_subscribers,
                        "pro": revenue_metrics.pro_subscribers,
                        "total_paid": revenue_metrics.total_active_subscribers
                    },
                    
                    "growth": {
                        "new_subscribers": revenue_metrics.new_subscribers,
                        "churned_subscribers": revenue_metrics.churned_subscribers,
                        "net_growth": revenue_metrics.net_subscriber_growth,
                        "conversion_rate": cohort_metrics.conversion_rate
                    },
                    
                    "churn": {
                        "voluntary_rate": revenue_metrics.voluntary_churn_rate,
                        "involuntary_rate": revenue_metrics.involuntary_churn_rate
                    }
                },
                
                "events": {
                    "by_type": {
                        event_type.value: count 
                        for event_type, count in event_counts.items()
                    },
                    "total": total_events
                },
                
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return dashboard_data
        
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            raise
    
    # Adherence analysis
    
    async def calculate_adherence_metrics(
        self,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate detailed adherence metrics."""
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Filter events
        events = self.analytics_service.events
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        events = [
            e for e in events 
            if start_date <= e.timestamp <= end_date
            and e.event_type in [EventType.PLAN_GENERATED, EventType.MEAL_LOGGED]
        ]
        
        # Group by user
        user_data = defaultdict(lambda: {"plans": 0, "meals": 0, "adherence": 0.0})
        
        for event in events:
            if not event.user_id:
                continue
                
            if event.event_type == EventType.PLAN_GENERATED:
                user_data[event.user_id]["plans"] += 1
            elif event.event_type == EventType.MEAL_LOGGED:
                status = event.properties.get("status", "unknown")
                if status == "eaten":
                    user_data[event.user_id]["meals"] += 1
        
        # Calculate adherence for each user
        adherence_scores = []
        for uid, data in user_data.items():
            if data["plans"] > 0:
                # Assuming 7 meals per plan (breakfast, lunch, dinner for 7 days + snacks)
                expected_meals = data["plans"] * 7
                adherence = min(data["meals"] / expected_meals, 1.0)
                data["adherence"] = adherence
                adherence_scores.append(adherence)
        
        # Calculate aggregate metrics
        total_users = len(user_data)
        if total_users == 0:
            return {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_users": 0,
                "average_adherence": 0.0,
                "median_adherence": 0.0,
                "adherence_distribution": {},
                "user_data": {}
            }
        
        adherence_scores.sort()
        average_adherence = sum(adherence_scores) / len(adherence_scores)
        median_adherence = adherence_scores[len(adherence_scores) // 2]
        
        # Adherence distribution
        distribution = {
            "0-20%": len([s for s in adherence_scores if s < 0.2]),
            "20-40%": len([s for s in adherence_scores if 0.2 <= s < 0.4]),
            "40-60%": len([s for s in adherence_scores if 0.4 <= s < 0.6]),
            "60-80%": len([s for s in adherence_scores if 0.6 <= s < 0.8]),
            "80-100%": len([s for s in adherence_scores if s >= 0.8])
        }
        
        result = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_users": total_users,
            "average_adherence": average_adherence,
            "median_adherence": median_adherence,
            "adherence_distribution": distribution,
            "user_data": {
                str(uid): data for uid, data in user_data.items()
            } if user_id else {}
        }
        
        return result
