"""
Post-Mortem Automation System
Generates automated post-mortem reports and tracks action items
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class PostMortemSeverity(Enum):
    """Severity levels requiring post-mortems"""
    REQUIRED = "required"    # SEV1, SEV2
    OPTIONAL = "optional"    # SEV3
    NOT_REQUIRED = "not_required"  # SEV4


@dataclass
class ActionItem:
    """Post-mortem action item"""
    id: str
    description: str
    owner: str
    due_date: datetime
    priority: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]


@dataclass
class PostMortem:
    """Post-mortem report structure"""
    id: str
    incident_id: str
    title: str
    summary: str
    timeline: List[Dict[str, Any]]
    root_cause: str
    contributing_factors: List[str]
    impact_assessment: Dict[str, Any]
    detection_time: float  # minutes
    resolution_time: float  # minutes
    action_items: List[ActionItem]
    lessons_learned: List[str]
    prevention_measures: List[str]
    created_at: datetime
    reviewed_by: List[str]
    approved: bool


class PostMortemService:
    """
    Automated post-mortem generation and tracking
    """
    
    def __init__(self):
        # AWS clients
        self.dynamodb = boto3.resource('dynamodb')
        self.sns = boto3.client('sns')
        self.s3 = boto3.client('s3')
        
        # Tables
        self.incidents_table = self.dynamodb.Table('ai-nutritionist-incidents')
        self.postmortems_table = self.dynamodb.Table('ai-nutritionist-postmortems')
        self.action_items_table = self.dynamodb.Table('ai-nutritionist-action-items')
        self.metrics_table = self.dynamodb.Table('ai-nutritionist-monitoring-metrics')
        
        # Configuration
        self.postmortem_config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load post-mortem configuration"""
        return {
            'auto_generate': {
                'sev1': True,
                'sev2': True,
                'sev3': False,
                'sev4': False
            },
            'required_reviewers': {
                'sev1': ['engineering-manager', 'director', 'cto'],
                'sev2': ['team-lead', 'engineering-manager'],
                'sev3': ['team-lead']
            },
            'sla_targets': {
                'detection_time': 300,  # 5 minutes
                'resolution_time': 3600,  # 1 hour for SEV1
                'postmortem_creation': 86400,  # 24 hours
                'action_item_completion': 604800  # 1 week
            },
            'templates': {
                'default': 'default_postmortem_template.md',
                'security': 'security_postmortem_template.md',
                'performance': 'performance_postmortem_template.md'
            }
        }
    
    async def should_generate_postmortem(self, incident_id: str) -> bool:
        """Determine if incident requires post-mortem"""
        try:
            # Get incident details
            response = self.incidents_table.get_item(
                Key={'incident_id': incident_id}
            )
            
            if 'Item' not in response:
                logger.warning(f"Incident {incident_id} not found")
                return False
            
            incident = response['Item']
            severity = incident.get('severity', 'sev4')
            
            # Check configuration
            return self.postmortem_config['auto_generate'].get(severity, False)
            
        except Exception as e:
            logger.error(f"Error checking post-mortem requirement: {e}")
            return False
    
    async def generate_postmortem(self, incident_id: str) -> Optional[PostMortem]:
        """Generate automated post-mortem report"""
        try:
            # Get incident data
            incident_data = await self._get_incident_data(incident_id)
            if not incident_data:
                return None
            
            # Gather additional data
            metrics_data = await self._gather_metrics_data(incident_data)
            timeline_data = await self._analyze_timeline(incident_data)
            impact_data = await self._assess_impact(incident_data, metrics_data)
            
            # Generate post-mortem
            postmortem = PostMortem(
                id=f"PM-{incident_id}",
                incident_id=incident_id,
                title=f"Post-Mortem: {incident_data.get('title', 'Unknown Incident')}",
                summary=await self._generate_summary(incident_data, impact_data),
                timeline=timeline_data,
                root_cause=await self._identify_root_cause(incident_data, metrics_data),
                contributing_factors=await self._identify_contributing_factors(incident_data, metrics_data),
                impact_assessment=impact_data,
                detection_time=timeline_data.get('detection_time', 0),
                resolution_time=timeline_data.get('resolution_time', 0),
                action_items=await self._generate_action_items(incident_data, metrics_data),
                lessons_learned=await self._extract_lessons_learned(incident_data),
                prevention_measures=await self._suggest_prevention_measures(incident_data),
                created_at=datetime.utcnow(),
                reviewed_by=[],
                approved=False
            )
            
            # Store post-mortem
            await self._store_postmortem(postmortem)
            
            # Send for review
            await self._send_for_review(postmortem)
            
            logger.info(f"Generated post-mortem {postmortem.id} for incident {incident_id}")
            return postmortem
            
        except Exception as e:
            logger.error(f"Error generating post-mortem for {incident_id}: {e}")
            return None
    
    async def _get_incident_data(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident data from DynamoDB"""
        try:
            response = self.incidents_table.get_item(
                Key={'incident_id': incident_id}
            )
            
            return response.get('Item')
            
        except Exception as e:
            logger.error(f"Error getting incident data: {e}")
            return None
    
    async def _gather_metrics_data(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gather relevant metrics data for the incident timeframe"""
        try:
            created_at = datetime.fromisoformat(incident_data.get('created_at', ''))
            resolved_at = datetime.fromisoformat(incident_data.get('resolved_at', '')) if incident_data.get('resolved_at') else datetime.utcnow()
            
            # Query metrics from the incident timeframe
            metrics_response = self.metrics_table.scan(
                FilterExpression='#timestamp BETWEEN :start AND :end',
                ExpressionAttributeNames={'#timestamp': 'timestamp'},
                ExpressionAttributeValues={
                    ':start': (created_at - timedelta(hours=1)).isoformat(),
                    ':end': (resolved_at + timedelta(hours=1)).isoformat()
                }
            )
            
            metrics = metrics_response.get('Items', [])
            
            # Organize metrics by type
            organized_metrics = {
                'error_rates': [],
                'response_times': [],
                'resource_utilization': [],
                'business_metrics': []
            }
            
            for metric in metrics:
                metric_name = metric.get('metric_name', '').lower()
                
                if 'error' in metric_name:
                    organized_metrics['error_rates'].append(metric)
                elif 'duration' in metric_name or 'latency' in metric_name:
                    organized_metrics['response_times'].append(metric)
                elif 'cpu' in metric_name or 'memory' in metric_name or 'capacity' in metric_name:
                    organized_metrics['resource_utilization'].append(metric)
                elif 'revenue' in metric_name or 'user' in metric_name:
                    organized_metrics['business_metrics'].append(metric)
            
            return organized_metrics
            
        except Exception as e:
            logger.error(f"Error gathering metrics data: {e}")
            return {}
    
    async def _analyze_timeline(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze incident timeline for key metrics"""
        try:
            timeline = incident_data.get('timeline', [])
            created_at = datetime.fromisoformat(incident_data.get('created_at', ''))
            resolved_at = datetime.fromisoformat(incident_data.get('resolved_at', '')) if incident_data.get('resolved_at') else datetime.utcnow()
            
            # Find detection time (time from incident start to detection)
            detection_event = next((event for event in timeline if 'detected' in event.get('event', '').lower()), None)
            detection_time = 0
            
            if detection_event:
                detection_timestamp = datetime.fromisoformat(detection_event['timestamp'])
                detection_time = (detection_timestamp - created_at).total_seconds() / 60  # minutes
            
            # Calculate resolution time
            resolution_time = (resolved_at - created_at).total_seconds() / 60  # minutes
            
            # Analyze timeline events
            timeline_analysis = {
                'detection_time': detection_time,
                'resolution_time': resolution_time,
                'total_events': len(timeline),
                'key_events': self._extract_key_events(timeline),
                'response_effectiveness': self._assess_response_effectiveness(timeline, resolution_time)
            }
            
            return timeline_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing timeline: {e}")
            return {}
    
    def _extract_key_events(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract key events from timeline"""
        key_events = []
        
        for event in timeline:
            event_text = event.get('event', '').lower()
            
            # Identify key event types
            if any(keyword in event_text for keyword in ['detected', 'escalated', 'resolved', 'mitigated']):
                key_events.append(event)
        
        return key_events
    
    def _assess_response_effectiveness(self, timeline: List[Dict[str, Any]], resolution_time: float) -> str:
        """Assess effectiveness of incident response"""
        sla_target = self.postmortem_config['sla_targets']['resolution_time'] / 60  # convert to minutes
        
        if resolution_time <= sla_target:
            return "Excellent - Resolved within SLA"
        elif resolution_time <= sla_target * 1.5:
            return "Good - Resolved within 150% of SLA"
        elif resolution_time <= sla_target * 2:
            return "Needs Improvement - Resolved within 200% of SLA"
        else:
            return "Poor - Significantly exceeded SLA"
    
    async def _assess_impact(self, incident_data: Dict[str, Any], metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess business and technical impact"""
        try:
            impact = {
                'affected_users': 0,
                'revenue_impact': 0,
                'service_degradation': [],
                'sla_breaches': [],
                'reputation_impact': 'Low'
            }
            
            # Analyze business metrics during incident
            business_metrics = metrics_data.get('business_metrics', [])
            
            # Calculate revenue impact
            revenue_metrics = [m for m in business_metrics if 'revenue' in m.get('metric_name', '').lower()]
            if revenue_metrics:
                # Simple calculation - could be more sophisticated
                avg_revenue = sum(float(m.get('value', 0)) for m in revenue_metrics) / len(revenue_metrics)
                impact['revenue_impact'] = max(0, 100 - avg_revenue)  # Assume 100 is baseline
            
            # Assess service degradation
            error_rates = metrics_data.get('error_rates', [])
            if error_rates:
                max_error_rate = max(float(m.get('value', 0)) for m in error_rates)
                if max_error_rate > 10:
                    impact['service_degradation'].append(f"High error rate: {max_error_rate}%")
            
            # Determine reputation impact based on severity and duration
            severity = incident_data.get('severity', 'sev4')
            created_at = datetime.fromisoformat(incident_data.get('created_at', ''))
            resolved_at = datetime.fromisoformat(incident_data.get('resolved_at', '')) if incident_data.get('resolved_at') else datetime.utcnow()
            duration_hours = (resolved_at - created_at).total_seconds() / 3600
            
            if severity in ['sev1', 'sev2'] and duration_hours > 2:
                impact['reputation_impact'] = 'High'
            elif severity in ['sev1', 'sev2'] or duration_hours > 4:
                impact['reputation_impact'] = 'Medium'
            
            return impact
            
        except Exception as e:
            logger.error(f"Error assessing impact: {e}")
            return {}
    
    async def _generate_summary(self, incident_data: Dict[str, Any], impact_data: Dict[str, Any]) -> str:
        """Generate incident summary"""
        summary_parts = []
        
        # Basic incident info
        severity = incident_data.get('severity', 'unknown').upper()
        title = incident_data.get('title', 'Unknown Incident')
        summary_parts.append(f"This {severity} incident involved {title}.")
        
        # Impact summary
        if impact_data.get('revenue_impact', 0) > 0:
            summary_parts.append(f"The incident resulted in an estimated revenue impact of ${impact_data['revenue_impact']:.2f}.")
        
        if impact_data.get('service_degradation'):
            summary_parts.append(f"Service degradation included: {', '.join(impact_data['service_degradation'])}.")
        
        # Resolution summary
        created_at = datetime.fromisoformat(incident_data.get('created_at', ''))
        resolved_at = datetime.fromisoformat(incident_data.get('resolved_at', '')) if incident_data.get('resolved_at') else datetime.utcnow()
        duration = resolved_at - created_at
        
        summary_parts.append(f"The incident was resolved after {duration}.")
        
        return " ".join(summary_parts)
    
    async def _identify_root_cause(self, incident_data: Dict[str, Any], metrics_data: Dict[str, Any]) -> str:
        """Identify root cause based on data analysis"""
        # Simple root cause identification - could use ML for better analysis
        
        affected_services = incident_data.get('affected_services', [])
        error_rates = metrics_data.get('error_rates', [])
        response_times = metrics_data.get('response_times', [])
        
        if any('lambda' in service.lower() for service in affected_services):
            if response_times and any(float(m.get('value', 0)) > 25000 for m in response_times):
                return "Lambda function timeout due to increased processing time"
            elif error_rates:
                return "Lambda function errors due to code or dependency issues"
        
        if any('dynamodb' in service.lower() for service in affected_services):
            return "DynamoDB throttling due to exceeded capacity limits"
        
        if any('api' in service.lower() for service in affected_services):
            return "API Gateway rate limiting or backend service issues"
        
        return "Root cause requires further investigation"
    
    async def _identify_contributing_factors(self, incident_data: Dict[str, Any], metrics_data: Dict[str, Any]) -> List[str]:
        """Identify contributing factors"""
        factors = []
        
        # Check for resource utilization issues
        utilization_metrics = metrics_data.get('resource_utilization', [])
        if utilization_metrics:
            high_utilization = [m for m in utilization_metrics if float(m.get('value', 0)) > 80]
            if high_utilization:
                factors.append("High resource utilization")
        
        # Check for cascade failures
        error_rates = metrics_data.get('error_rates', [])
        if len(error_rates) > 5:  # Multiple services with errors
            factors.append("Cascade failure across multiple services")
        
        # Check timing
        created_at = datetime.fromisoformat(incident_data.get('created_at', ''))
        if created_at.hour in [8, 9, 17, 18]:  # Peak hours
            factors.append("Occurred during peak traffic hours")
        
        if created_at.weekday() == 0:  # Monday
            factors.append("Monday traffic spike")
        
        return factors or ["No significant contributing factors identified"]
    
    async def _generate_action_items(self, incident_data: Dict[str, Any], metrics_data: Dict[str, Any]) -> List[ActionItem]:
        """Generate action items based on incident analysis"""
        action_items = []
        now = datetime.utcnow()
        
        # Standard action items based on incident type
        severity = incident_data.get('severity', 'sev4')
        
        if severity in ['sev1', 'sev2']:
            action_items.append(ActionItem(
                id=f"AI-{incident_data['incident_id']}-001",
                description="Review and update monitoring thresholds",
                owner="platform-team",
                due_date=now + timedelta(days=7),
                priority="High",
                status="Open",
                created_at=now,
                completed_at=None
            ))
            
            action_items.append(ActionItem(
                id=f"AI-{incident_data['incident_id']}-002",
                description="Implement additional automated recovery procedures",
                owner="engineering-team",
                due_date=now + timedelta(days=14),
                priority="Medium",
                status="Open",
                created_at=now,
                completed_at=None
            ))
        
        # Specific action items based on root cause
        affected_services = incident_data.get('affected_services', [])
        
        if any('lambda' in service.lower() for service in affected_services):
            action_items.append(ActionItem(
                id=f"AI-{incident_data['incident_id']}-003",
                description="Optimize Lambda function performance and timeout settings",
                owner="backend-team",
                due_date=now + timedelta(days=10),
                priority="High",
                status="Open",
                created_at=now,
                completed_at=None
            ))
        
        if any('dynamodb' in service.lower() for service in affected_services):
            action_items.append(ActionItem(
                id=f"AI-{incident_data['incident_id']}-004",
                description="Review DynamoDB capacity planning and auto-scaling configuration",
                owner="database-team",
                due_date=now + timedelta(days=7),
                priority="High",
                status="Open",
                created_at=now,
                completed_at=None
            ))
        
        return action_items
    
    async def _extract_lessons_learned(self, incident_data: Dict[str, Any]) -> List[str]:
        """Extract lessons learned from incident"""
        lessons = []
        
        # Analyze response timeline
        timeline = incident_data.get('timeline', [])
        
        # Check detection time
        created_at = datetime.fromisoformat(incident_data.get('created_at', ''))
        detection_event = next((event for event in timeline if 'detected' in event.get('event', '').lower()), None)
        
        if detection_event:
            detection_time = datetime.fromisoformat(detection_event['timestamp'])
            detection_delay = (detection_time - created_at).total_seconds() / 60
            
            if detection_delay > 5:  # 5 minutes
                lessons.append(f"Incident detection took {detection_delay:.1f} minutes - consider improving monitoring sensitivity")
        
        # Check escalation effectiveness
        escalation_events = [event for event in timeline if 'escalat' in event.get('event', '').lower()]
        if not escalation_events:
            lessons.append("No escalation events recorded - consider improving escalation procedures")
        
        # Check automated response
        automated_events = [event for event in timeline if 'automat' in event.get('event', '').lower()]
        if not automated_events:
            lessons.append("No automated response recorded - consider implementing automated recovery")
        
        return lessons or ["Incident was handled according to standard procedures"]
    
    async def _suggest_prevention_measures(self, incident_data: Dict[str, Any]) -> List[str]:
        """Suggest prevention measures"""
        measures = []
        
        affected_services = incident_data.get('affected_services', [])
        severity = incident_data.get('severity', 'sev4')
        
        if severity in ['sev1', 'sev2']:
            measures.append("Implement chaos engineering tests for affected services")
            measures.append("Add synthetic monitoring for critical user journeys")
        
        if any('lambda' in service.lower() for service in affected_services):
            measures.append("Implement Lambda function warming and concurrency management")
            measures.append("Add detailed Lambda performance monitoring")
        
        if any('dynamodb' in service.lower() for service in affected_services):
            measures.append("Implement predictive capacity scaling for DynamoDB")
            measures.append("Add DynamoDB performance insights monitoring")
        
        measures.append("Conduct quarterly disaster recovery drills")
        measures.append("Review and update incident response runbooks")
        
        return measures
    
    async def _store_postmortem(self, postmortem: PostMortem) -> bool:
        """Store post-mortem in DynamoDB"""
        try:
            # Store post-mortem
            self.postmortems_table.put_item(
                Item={
                    'postmortem_id': postmortem.id,
                    'incident_id': postmortem.incident_id,
                    'title': postmortem.title,
                    'summary': postmortem.summary,
                    'timeline': postmortem.timeline,
                    'root_cause': postmortem.root_cause,
                    'contributing_factors': postmortem.contributing_factors,
                    'impact_assessment': postmortem.impact_assessment,
                    'detection_time': postmortem.detection_time,
                    'resolution_time': postmortem.resolution_time,
                    'lessons_learned': postmortem.lessons_learned,
                    'prevention_measures': postmortem.prevention_measures,
                    'created_at': postmortem.created_at.isoformat(),
                    'reviewed_by': postmortem.reviewed_by,
                    'approved': postmortem.approved
                }
            )
            
            # Store action items
            for action_item in postmortem.action_items:
                self.action_items_table.put_item(
                    Item={
                        'action_item_id': action_item.id,
                        'postmortem_id': postmortem.id,
                        'description': action_item.description,
                        'owner': action_item.owner,
                        'due_date': action_item.due_date.isoformat(),
                        'priority': action_item.priority,
                        'status': action_item.status,
                        'created_at': action_item.created_at.isoformat(),
                        'completed_at': action_item.completed_at.isoformat() if action_item.completed_at else None
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing post-mortem: {e}")
            return False
    
    async def _send_for_review(self, postmortem: PostMortem) -> bool:
        """Send post-mortem for review"""
        try:
            # Get severity from incident ID
            incident_response = self.incidents_table.get_item(
                Key={'incident_id': postmortem.incident_id}
            )
            
            if 'Item' not in incident_response:
                return False
            
            severity = incident_response['Item'].get('severity', 'sev4')
            reviewers = self.postmortem_config['required_reviewers'].get(severity, [])
            
            # Send notification to reviewers
            message = f"""
            Post-Mortem Ready for Review
            
            Post-Mortem ID: {postmortem.id}
            Incident: {postmortem.title}
            
            Summary: {postmortem.summary}
            
            Root Cause: {postmortem.root_cause}
            
            Action Items: {len(postmortem.action_items)}
            
            Please review and approve this post-mortem.
            """
            
            # Send to SNS topic for reviewers
            self.sns.publish(
                TopicArn='arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-postmortem-reviews',
                Message=message,
                Subject=f"Post-Mortem Review Required: {postmortem.title}"
            )
            
            logger.info(f"Sent post-mortem {postmortem.id} for review to {reviewers}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending post-mortem for review: {e}")
            return False
    
    async def track_action_items(self) -> Dict[str, Any]:
        """Track action item completion"""
        try:
            # Query overdue action items
            now = datetime.utcnow()
            
            # Scan action items table for overdue items
            response = self.action_items_table.scan(
                FilterExpression='#status = :status AND due_date < :now',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'Open',
                    ':now': now.isoformat()
                }
            )
            
            overdue_items = response.get('Items', [])
            
            # Send reminders for overdue items
            for item in overdue_items:
                await self._send_action_item_reminder(item)
            
            # Calculate completion metrics
            all_items_response = self.action_items_table.scan()
            all_items = all_items_response.get('Items', [])
            
            completed_items = [item for item in all_items if item.get('status') == 'Completed']
            completion_rate = len(completed_items) / len(all_items) if all_items else 0
            
            return {
                'total_action_items': len(all_items),
                'completed_items': len(completed_items),
                'overdue_items': len(overdue_items),
                'completion_rate': completion_rate,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error tracking action items: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_action_item_reminder(self, action_item: Dict[str, Any]) -> bool:
        """Send reminder for overdue action item"""
        try:
            message = f"""
            Overdue Action Item Reminder
            
            Action Item: {action_item.get('description')}
            Owner: {action_item.get('owner')}
            Due Date: {action_item.get('due_date')}
            Priority: {action_item.get('priority')}
            
            This action item is overdue. Please update the status or provide an update.
            """
            
            self.sns.publish(
                TopicArn='arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-action-item-reminders',
                Message=message,
                Subject=f"Overdue Action Item: {action_item.get('description')[:50]}..."
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending action item reminder: {e}")
            return False


# Lambda handler for post-mortem generation
async def postmortem_handler(event, context):
    """Lambda handler for post-mortem generation"""
    postmortem_service = PostMortemService()
    
    try:
        if 'incident_id' in event:
            incident_id = event['incident_id']
            
            # Check if post-mortem is required
            if await postmortem_service.should_generate_postmortem(incident_id):
                postmortem = await postmortem_service.generate_postmortem(incident_id)
                
                if postmortem:
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': f'Post-mortem generated: {postmortem.id}',
                            'postmortem_id': postmortem.id
                        })
                    }
                else:
                    return {
                        'statusCode': 500,
                        'body': json.dumps({'error': 'Failed to generate post-mortem'})
                    }
            else:
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Post-mortem not required for this incident'})
                }
        
        # If no incident_id, track action items
        tracking_results = await postmortem_service.track_action_items()
        
        return {
            'statusCode': 200,
            'body': json.dumps(tracking_results)
        }
        
    except Exception as e:
        logger.error(f"Error in post-mortem handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        service = PostMortemService()
        
        # Test post-mortem generation
        test_incident_id = "INC-1697299200"
        
        if await service.should_generate_postmortem(test_incident_id):
            postmortem = await service.generate_postmortem(test_incident_id)
            if postmortem:
                print(f"Generated post-mortem: {postmortem.id}")
                print(f"Action items: {len(postmortem.action_items)}")
        
        # Test action item tracking
        tracking_results = await service.track_action_items()
        print(json.dumps(tracking_results, indent=2))
    
    asyncio.run(main())
