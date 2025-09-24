"""Fitness integration service for Track D3.

Imports daily fitness summaries (steps, workout) to adjust recovery meals.
Optional integration behind feature flag.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import asyncio

import httpx
from dataclasses import asdict

from ...models.integrations import (
    FitnessData,
    FitnessProvider,
    OAuthCredentials,
    WorkoutSession,
    WorkoutType
)


logger = logging.getLogger(__name__)


class FitnessAuthService:
    """Handles OAuth authentication for fitness providers."""
    
    def __init__(self):
        # OAuth configuration for fitness providers
        self.oauth_configs = {
            FitnessProvider.APPLE_HEALTH: {
                # Apple Health requires HealthKit integration (iOS only)
                "scope": "health.read",
                "auth_method": "healthkit"
            },
            FitnessProvider.GOOGLE_FIT: {
                "client_id": "your-google-fit-client-id",
                "client_secret": "your-google-fit-client-secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scope": "https://www.googleapis.com/auth/fitness.activity.read https://www.googleapis.com/auth/fitness.body.read"
            },
            FitnessProvider.FITBIT: {
                "client_id": "your-fitbit-client-id",
                "client_secret": "your-fitbit-client-secret",
                "auth_uri": "https://www.fitbit.com/oauth2/authorize",
                "token_uri": "https://api.fitbit.com/oauth2/token",
                "scope": "activity heartrate nutrition profile settings sleep social weight"
            },
            FitnessProvider.GARMIN: {
                "client_id": "your-garmin-client-id",
                "client_secret": "your-garmin-client-secret",
                "auth_uri": "https://connect.garmin.com/oauthConfirm",
                "token_uri": "https://connectapi.garmin.com/oauth-service/oauth/access_token",
                "scope": "read"
            },
            FitnessProvider.STRAVA: {
                "client_id": "your-strava-client-id",
                "client_secret": "your-strava-client-secret",
                "auth_uri": "https://www.strava.com/oauth/authorize",
                "token_uri": "https://www.strava.com/oauth/token",
                "scope": "read,activity:read"
            }
        }
    
    def get_authorization_url(self, provider: FitnessProvider, user_id: UUID,
                            redirect_uri: str) -> str:
        """Generate OAuth authorization URL for fitness provider."""
        if provider == FitnessProvider.APPLE_HEALTH:
            # Apple Health requires native iOS integration
            return "app://health-kit-auth"
        
        config = self.oauth_configs[provider]
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": config["scope"],
            "response_type": "code",
            "state": f"{user_id}:{provider.value}"
        }
        
        from urllib.parse import urlencode
        return f"{config['auth_uri']}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, provider: FitnessProvider,
                                     code: str, redirect_uri: str) -> OAuthCredentials:
        """Exchange authorization code for access/refresh tokens."""
        if provider == FitnessProvider.APPLE_HEALTH:
            # Apple Health uses HealthKit, not OAuth
            return OAuthCredentials(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                provider=provider,
                access_token="healthkit_authorized",
                scope=["health.read"]
            )
        
        config = self.oauth_configs[provider]
        
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(config["token_uri"], data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            return OAuthCredentials(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be set by caller
                provider=provider,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expires_at=(
                    datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
                    if token_data.get("expires_in") else None
                ),
                scope=token_data.get("scope", "").split() if token_data.get("scope") else []
            )


class FitnessDataImporter:
    """Imports fitness data from various providers."""
    
    def __init__(self, auth_service: FitnessAuthService):
        self.auth_service = auth_service
    
    async def import_daily_data(self, credentials: OAuthCredentials,
                              date: datetime) -> FitnessData:
        """Import fitness data for a specific date."""
        if credentials.provider == FitnessProvider.GOOGLE_FIT:
            return await self._import_google_fit_data(credentials, date)
        elif credentials.provider == FitnessProvider.FITBIT:
            return await self._import_fitbit_data(credentials, date)
        elif credentials.provider == FitnessProvider.APPLE_HEALTH:
            return await self._import_apple_health_data(credentials, date)
        elif credentials.provider == FitnessProvider.STRAVA:
            return await self._import_strava_data(credentials, date)
        elif credentials.provider == FitnessProvider.GARMIN:
            return await self._import_garmin_data(credentials, date)
        else:
            raise ValueError(f"Unsupported fitness provider: {credentials.provider}")
    
    async def _import_google_fit_data(self, credentials: OAuthCredentials,
                                    date: datetime) -> FitnessData:
        """Import data from Google Fit."""
        headers = {
            "Authorization": f"Bearer {credentials.access_token}",
            "Content-Type": "application/json"
        }
        
        # Calculate time range for the day
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        start_nanos = int(start_time.timestamp() * 1_000_000_000)
        end_nanos = int(end_time.timestamp() * 1_000_000_000)
        
        fitness_data = FitnessData(
            user_id=credentials.user_id,
            date=start_time,
            provider=FitnessProvider.GOOGLE_FIT
        )
        
        async with httpx.AsyncClient() as client:
            # Get steps data
            steps_url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
            steps_request = {
                "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
                "bucketByTime": {"durationMillis": 86400000},  # 1 day
                "startTimeMillis": start_nanos // 1_000_000,
                "endTimeMillis": end_nanos // 1_000_000
            }
            
            try:
                response = await client.post(steps_url, headers=headers, json=steps_request)
                if response.status_code == 200:
                    steps_data = response.json()
                    if steps_data.get("bucket") and steps_data["bucket"][0].get("dataset"):
                        for dataset in steps_data["bucket"][0]["dataset"]:
                            if dataset.get("point"):
                                steps = sum(point["value"][0]["intVal"] for point in dataset["point"])
                                fitness_data.steps = steps
            except Exception as e:
                logger.warning(f"Failed to get steps from Google Fit: {e}")
            
            # Get calories data
            calories_url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
            calories_request = {
                "aggregateBy": [{"dataTypeName": "com.google.calories.expended"}],
                "bucketByTime": {"durationMillis": 86400000},
                "startTimeMillis": start_nanos // 1_000_000,
                "endTimeMillis": end_nanos // 1_000_000
            }
            
            try:
                response = await client.post(calories_url, headers=headers, json=calories_request)
                if response.status_code == 200:
                    calories_data = response.json()
                    if calories_data.get("bucket") and calories_data["bucket"][0].get("dataset"):
                        for dataset in calories_data["bucket"][0]["dataset"]:
                            if dataset.get("point"):
                                calories = sum(point["value"][0]["fpVal"] for point in dataset["point"])
                                fitness_data.calories_burned = int(calories)
            except Exception as e:
                logger.warning(f"Failed to get calories from Google Fit: {e}")
        
        # Calculate derived metrics
        fitness_data.activity_level = fitness_data.calculate_activity_level()
        fitness_data.recovery_needed = fitness_data.needs_recovery_nutrition()
        
        return fitness_data
    
    async def _import_fitbit_data(self, credentials: OAuthCredentials,
                                date: datetime) -> FitnessData:
        """Import data from Fitbit."""
        headers = {
            "Authorization": f"Bearer {credentials.access_token}"
        }
        
        date_str = date.strftime("%Y-%m-%d")
        
        fitness_data = FitnessData(
            user_id=credentials.user_id,
            date=date.replace(hour=0, minute=0, second=0, microsecond=0),
            provider=FitnessProvider.FITBIT
        )
        
        async with httpx.AsyncClient() as client:
            # Get activity summary
            try:
                activity_url = f"https://api.fitbit.com/1/user/-/activities/date/{date_str}.json"
                response = await client.get(activity_url, headers=headers)
                if response.status_code == 200:
                    activity_data = response.json()
                    summary = activity_data.get("summary", {})
                    
                    fitness_data.steps = summary.get("steps")
                    fitness_data.calories_burned = summary.get("caloriesOut")
                    fitness_data.distance_km = Decimal(str(summary.get("distances", [{}])[0].get("distance", 0)))
                    fitness_data.active_minutes = summary.get("veryActiveMinutes", 0) + summary.get("fairlyActiveMinutes", 0)
            except Exception as e:
                logger.warning(f"Failed to get activity data from Fitbit: {e}")
            
            # Get heart rate data
            try:
                hr_url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date_str}/1d.json"
                response = await client.get(hr_url, headers=headers)
                if response.status_code == 200:
                    hr_data = response.json()
                    if hr_data.get("activities-heart"):
                        resting_hr = hr_data["activities-heart"][0].get("value", {}).get("restingHeartRate")
                        fitness_data.resting_heart_rate = resting_hr
            except Exception as e:
                logger.warning(f"Failed to get heart rate data from Fitbit: {e}")
            
            # Get sleep data
            try:
                sleep_url = f"https://api.fitbit.com/1.2/user/-/sleep/date/{date_str}.json"
                response = await client.get(sleep_url, headers=headers)
                if response.status_code == 200:
                    sleep_data = response.json()
                    if sleep_data.get("sleep"):
                        total_minutes = sum(sleep["minutesAsleep"] for sleep in sleep_data["sleep"])
                        fitness_data.sleep_hours = Decimal(str(total_minutes / 60))
            except Exception as e:
                logger.warning(f"Failed to get sleep data from Fitbit: {e}")
        
        # Calculate derived metrics
        fitness_data.activity_level = fitness_data.calculate_activity_level()
        fitness_data.recovery_needed = fitness_data.needs_recovery_nutrition()
        
        return fitness_data
    
    async def _import_apple_health_data(self, credentials: OAuthCredentials,
                                      date: datetime) -> FitnessData:
        """Import data from Apple Health (placeholder for HealthKit integration)."""
        # In a real implementation, this would use HealthKit APIs through iOS
        # For now, return mock data
        fitness_data = FitnessData(
            user_id=credentials.user_id,
            date=date.replace(hour=0, minute=0, second=0, microsecond=0),
            provider=FitnessProvider.APPLE_HEALTH,
            steps=8500,
            distance_km=Decimal("6.8"),
            calories_burned=450,
            active_minutes=65,
            resting_heart_rate=68,
            sleep_hours=Decimal("7.5")
        )
        
        # Add sample workout
        fitness_data.workouts = [
            WorkoutSession(
                workout_type=WorkoutType.RUNNING,
                duration_minutes=35,
                calories_burned=320,
                intensity="moderate",
                heart_rate_avg=145,
                heart_rate_max=162
            )
        ]
        
        fitness_data.activity_level = fitness_data.calculate_activity_level()
        fitness_data.recovery_needed = fitness_data.needs_recovery_nutrition()
        
        return fitness_data
    
    async def _import_strava_data(self, credentials: OAuthCredentials,
                                date: datetime) -> FitnessData:
        """Import data from Strava."""
        headers = {
            "Authorization": f"Bearer {credentials.access_token}"
        }
        
        # Calculate time range
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        fitness_data = FitnessData(
            user_id=credentials.user_id,
            date=start_time,
            provider=FitnessProvider.STRAVA
        )
        
        async with httpx.AsyncClient() as client:
            # Get activities for the date
            try:
                activities_url = "https://www.strava.com/api/v3/athlete/activities"
                params = {
                    "after": int(start_time.timestamp()),
                    "before": int(end_time.timestamp())
                }
                
                response = await client.get(activities_url, headers=headers, params=params)
                if response.status_code == 200:
                    activities = response.json()
                    
                    total_distance = 0
                    total_calories = 0
                    total_time = 0
                    workouts = []
                    
                    for activity in activities:
                        # Convert Strava activity to workout session
                        workout_type = self._strava_type_to_workout_type(activity.get("type", ""))
                        
                        workout = WorkoutSession(
                            workout_type=workout_type,
                            duration_minutes=activity.get("moving_time", 0) // 60,
                            calories_burned=activity.get("calories"),
                            intensity="moderate",  # Strava doesn't provide intensity directly
                            start_time=datetime.fromisoformat(activity.get("start_date", "").replace("Z", "+00:00")),
                            notes=activity.get("name", "")
                        )
                        workouts.append(workout)
                        
                        total_distance += activity.get("distance", 0) / 1000  # Convert to km
                        total_calories += activity.get("calories", 0)
                        total_time += activity.get("moving_time", 0) // 60
                    
                    fitness_data.workouts = workouts
                    fitness_data.distance_km = Decimal(str(total_distance))
                    fitness_data.calories_burned = total_calories
                    fitness_data.active_minutes = total_time
                    
            except Exception as e:
                logger.warning(f"Failed to get activities from Strava: {e}")
        
        fitness_data.activity_level = fitness_data.calculate_activity_level()
        fitness_data.recovery_needed = fitness_data.needs_recovery_nutrition()
        
        return fitness_data
    
    async def _import_garmin_data(self, credentials: OAuthCredentials,
                                date: datetime) -> FitnessData:
        """Import data from Garmin (placeholder)."""
        # Garmin Connect IQ API implementation would go here
        # For now, return mock data
        fitness_data = FitnessData(
            user_id=credentials.user_id,
            date=date.replace(hour=0, minute=0, second=0, microsecond=0),
            provider=FitnessProvider.GARMIN,
            steps=12500,
            distance_km=Decimal("10.2"),
            calories_burned=650,
            active_minutes=90,
            resting_heart_rate=62,
            sleep_hours=Decimal("8.2")
        )
        
        fitness_data.activity_level = fitness_data.calculate_activity_level()
        fitness_data.recovery_needed = fitness_data.needs_recovery_nutrition()
        
        return fitness_data
    
    def _strava_type_to_workout_type(self, strava_type: str) -> WorkoutType:
        """Convert Strava activity type to WorkoutType."""
        type_mapping = {
            "Run": WorkoutType.RUNNING,
            "Ride": WorkoutType.CYCLING,
            "Swim": WorkoutType.SWIMMING,
            "Walk": WorkoutType.WALKING,
            "Hike": WorkoutType.WALKING,
            "WeightTraining": WorkoutType.STRENGTH,
            "Yoga": WorkoutType.YOGA,
            "Workout": WorkoutType.HIIT
        }
        
        return type_mapping.get(strava_type, WorkoutType.OTHER)


class NutritionAdjustmentService:
    """Adjusts meal recommendations based on fitness data."""
    
    def __init__(self):
        # Recovery meal templates
        self.recovery_templates = {
            "high_protein": {
                "protein_multiplier": 1.5,
                "carb_multiplier": 1.2,
                "suggestions": [
                    "Grilled chicken with quinoa and vegetables",
                    "Greek yogurt with berries and nuts",
                    "Lean beef with sweet potato",
                    "Protein smoothie with banana and spinach"
                ]
            },
            "anti_inflammatory": {
                "omega3_focus": True,
                "antioxidant_focus": True,
                "suggestions": [
                    "Salmon with turmeric rice and broccoli",
                    "Chia seed pudding with blueberries",
                    "Spinach salad with walnuts and olive oil",
                    "Green tea and ginger smoothie"
                ]
            },
            "light": {
                "protein_multiplier": 0.8,
                "carb_multiplier": 0.7,
                "suggestions": [
                    "Light vegetable soup with whole grain crackers",
                    "Fruit and yogurt parfait", 
                    "Hummus with vegetable sticks",
                    "Green smoothie with cucumber and mint"
                ]
            }
        }
    
    def get_nutrition_adjustments(self, fitness_data: FitnessData,
                                preference: str = "high_protein") -> Dict:
        """Get nutrition adjustments based on fitness data."""
        adjustments = {
            "calories_adjustment": 0,
            "protein_adjustment": 0,
            "carb_adjustment": 0,
            "hydration_reminder": False,
            "recovery_focus": False,
            "meal_suggestions": [],
            "reasoning": []
        }
        
        activity_level = fitness_data.calculate_activity_level()
        needs_recovery = fitness_data.needs_recovery_nutrition()
        
        # Calorie adjustments based on activity
        if activity_level == "very_high":
            adjustments["calories_adjustment"] = 500
            adjustments["reasoning"].append("Very high activity - increased calorie needs")
        elif activity_level == "high":
            adjustments["calories_adjustment"] = 300
            adjustments["reasoning"].append("High activity - moderate calorie increase")
        elif activity_level == "moderate":
            adjustments["calories_adjustment"] = 100
            adjustments["reasoning"].append("Moderate activity - slight calorie increase")
        
        # Protein adjustments for strength training
        strength_workouts = [w for w in fitness_data.workouts 
                           if w.workout_type in [WorkoutType.STRENGTH, WorkoutType.HIIT]]
        if strength_workouts:
            adjustments["protein_adjustment"] = 20  # grams
            adjustments["reasoning"].append("Strength training detected - increased protein needs")
        
        # Carb adjustments for endurance activities
        endurance_workouts = [w for w in fitness_data.workouts
                            if w.workout_type in [WorkoutType.RUNNING, WorkoutType.CYCLING]
                            and w.duration_minutes > 60]
        if endurance_workouts:
            adjustments["carb_adjustment"] = 50  # grams
            adjustments["reasoning"].append("Endurance training detected - increased carb needs")
        
        # Recovery-focused nutrition
        if needs_recovery:
            adjustments["recovery_focus"] = True
            adjustments["hydration_reminder"] = True
            adjustments["reasoning"].append("Recovery nutrition recommended")
            
            template = self.recovery_templates[preference]
            adjustments["meal_suggestions"] = template["suggestions"]
            
            if "protein_multiplier" in template:
                adjustments["protein_adjustment"] *= template["protein_multiplier"]
            if "carb_multiplier" in template:
                adjustments["carb_adjustment"] *= template["carb_multiplier"]
        
        # Hydration reminders for high activity
        if fitness_data.calories_burned and fitness_data.calories_burned > 400:
            adjustments["hydration_reminder"] = True
            adjustments["reasoning"].append("High calorie burn - increased hydration needs")
        
        # Sleep quality impact
        if fitness_data.sleep_hours and fitness_data.sleep_hours < Decimal("7"):
            adjustments["meal_suggestions"].append("Foods rich in magnesium and tryptophan for better sleep")
            adjustments["reasoning"].append("Poor sleep detected - sleep-supporting nutrition")
        
        return adjustments


class FitnessService:
    """Main fitness integration service for Track D3."""
    
    def __init__(self):
        self.auth_service = FitnessAuthService()
        self.data_importer = FitnessDataImporter(self.auth_service)
        self.nutrition_service = NutritionAdjustmentService()
        
        # Feature flag for fitness integration
        self.fitness_enabled = True  # Would be loaded from feature flag service
        
        # In-memory storage for demo (would use database in production)
        self.credentials_store: Dict[UUID, OAuthCredentials] = {}
        self.fitness_data_store: Dict[Tuple[UUID, str], FitnessData] = {}  # (user_id, date_str)
    
    def is_enabled(self) -> bool:
        """Check if fitness integration is enabled via feature flag."""
        return self.fitness_enabled
    
    async def connect_fitness_provider(self, user_id: UUID, provider: FitnessProvider,
                                     authorization_code: str, redirect_uri: str) -> OAuthCredentials:
        """Connect user's fitness provider account."""
        if not self.is_enabled():
            raise ValueError("Fitness integration is disabled")
        
        # Exchange code for tokens
        credentials = await self.auth_service.exchange_code_for_tokens(
            provider, authorization_code, redirect_uri
        )
        
        # Update with user ID and store
        credentials = OAuthCredentials(
            user_id=user_id,
            provider=credentials.provider,
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            token_expires_at=credentials.token_expires_at,
            scope=credentials.scope
        )
        
        self.credentials_store[user_id] = credentials
        return credentials
    
    async def sync_daily_fitness_data(self, user_id: UUID, 
                                    date: Optional[datetime] = None) -> Optional[FitnessData]:
        """Sync fitness data for a specific date."""
        if not self.is_enabled():
            return None
        
        if user_id not in self.credentials_store:
            raise ValueError("Fitness provider not connected for user")
        
        if date is None:
            date = datetime.now()
        
        credentials = self.credentials_store[user_id]
        
        try:
            fitness_data = await self.data_importer.import_daily_data(credentials, date)
            
            # Store the data
            date_key = date.strftime("%Y-%m-%d")
            self.fitness_data_store[(user_id, date_key)] = fitness_data
            
            return fitness_data
            
        except Exception as e:
            logger.error(f"Failed to sync fitness data for user {user_id}: {e}")
            return None
    
    def get_fitness_data(self, user_id: UUID, date: datetime) -> Optional[FitnessData]:
        """Get fitness data for a specific date."""
        if not self.is_enabled():
            return None
        
        date_key = date.strftime("%Y-%m-%d")
        return self.fitness_data_store.get((user_id, date_key))
    
    def get_nutrition_adjustments(self, user_id: UUID, date: datetime,
                                preference: str = "high_protein") -> Optional[Dict]:
        """Get nutrition adjustments based on fitness data."""
        if not self.is_enabled():
            return None
        
        fitness_data = self.get_fitness_data(user_id, date)
        if not fitness_data:
            return None
        
        return self.nutrition_service.get_nutrition_adjustments(fitness_data, preference)
    
    def get_user_fitness_history(self, user_id: UUID, days: int = 7) -> List[FitnessData]:
        """Get fitness data history for a user."""
        if not self.is_enabled():
            return []
        
        history = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            
            if (user_id, date_key) in self.fitness_data_store:
                history.append(self.fitness_data_store[(user_id, date_key)])
        
        return sorted(history, key=lambda d: d.date, reverse=True)
    
    def get_authorization_url(self, user_id: UUID, provider: FitnessProvider,
                            redirect_uri: str) -> str:
        """Get OAuth authorization URL for fitness provider."""
        if not self.is_enabled():
            raise ValueError("Fitness integration is disabled")
        
        return self.auth_service.get_authorization_url(provider, user_id, redirect_uri)
    
    def calculate_weekly_activity_summary(self, user_id: UUID) -> Dict:
        """Calculate weekly activity summary."""
        if not self.is_enabled():
            return {}
        
        history = self.get_user_fitness_history(user_id, 7)
        
        if not history:
            return {}
        
        total_steps = sum(d.steps or 0 for d in history)
        total_calories = sum(d.calories_burned or 0 for d in history)
        total_workouts = sum(len(d.workouts) for d in history)
        avg_sleep = sum(d.sleep_hours or Decimal("0") for d in history) / len(history)
        
        activity_levels = [d.activity_level for d in history]
        high_activity_days = len([level for level in activity_levels if level in ["high", "very_high"]])
        
        recovery_days = len([d for d in history if d.recovery_needed])
        
        return {
            "total_steps": total_steps,
            "total_calories": total_calories,
            "total_workouts": total_workouts,
            "average_sleep_hours": float(avg_sleep),
            "high_activity_days": high_activity_days,
            "recovery_days_needed": recovery_days,
            "weekly_consistency": len(history) / 7.0,  # Percentage of days with data
            "recommendations": self._generate_weekly_recommendations(history)
        }
    
    def _generate_weekly_recommendations(self, history: List[FitnessData]) -> List[str]:
        """Generate weekly nutrition recommendations based on fitness patterns."""
        recommendations = []
        
        if not history:
            return recommendations
        
        # Check for consistent high activity
        high_activity_days = len([d for d in history if d.activity_level in ["high", "very_high"]])
        if high_activity_days >= 5:
            recommendations.append("Consider increasing overall caloric intake due to consistent high activity")
        
        # Check for recovery patterns
        recovery_days = len([d for d in history if d.recovery_needed])
        if recovery_days >= 3:
            recommendations.append("Focus on anti-inflammatory foods and adequate protein for recovery")
        
        # Check sleep patterns
        poor_sleep_days = len([d for d in history if d.sleep_hours and d.sleep_hours < Decimal("7")])
        if poor_sleep_days >= 3:
            recommendations.append("Consider foods that support sleep quality (magnesium, tryptophan)")
        
        # Check workout intensity
        intense_workouts = sum(len([w for w in d.workouts if w.intensity == "high"]) for d in history)
        if intense_workouts >= 3:
            recommendations.append("Ensure adequate protein intake for muscle recovery")
        
        return recommendations


# Export the main service
__all__ = ["FitnessService", "FitnessAuthService", "FitnessDataImporter", "NutritionAdjustmentService"]
