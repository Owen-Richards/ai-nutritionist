"""
Incident Response Automation System
Handles automated incident detection, escalation, and response procedures
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

import boto3
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels"""
    SEV1 = "sev1"  # Critical - Service down or major functionality broken
    SEV2 = "sev2"  # High - Significant functionality impacted
    SEV3 = "sev3"  # Medium - Minor functionality impacted
    SEV4 = "sev4"  # Low - Cosmetic or minor issues


class IncidentStatus(Enum):
    """Incident status"""
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class ResponseAction(Enum):
    """Automated response actions"""
    SCALE_OUT = "scale_out"
    RESTART_SERVICE = "restart_service"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    CIRCUIT_BREAKER = "circuit_breaker"
    ALERT_TEAM = "alert_team"
    CREATE_TICKET = "create_ticket"


@dataclass
class Incident:
    """Incident data structure"""
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    affected_services: List[str]
    root_cause: Optional[str]
    timeline: List[Dict[str, Any]]
    responders: List[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    tags: Dict[str, str]


@dataclass
class Runbook:
    """Automated runbook for incident response"""
    name: str
    trigger_conditions: Dict[str, Any]
    automated_actions: List[ResponseAction]
    escalation_rules: Dict[str, Any]
    required_approvals: List[str]
    rollback_procedure: List[str]


class IncidentResponseService:
    """
    Automated incident response and escalation system
    """
    
    def __init__(self):
        # AWS clients
        self.dynamodb = boto3.resource('dynamodb')
        self.lambda_client = boto3.client('lambda')
        self.ecs = boto3.client('ecs')
        self.autoscaling = boto3.client('application-autoscaling')
        self.sns = boto3.client('sns')
        self.ssm = boto3.client('ssm')
        
        # Tables
        self.incidents_table = self.dynamodb.Table('ai-nutritionist-incidents')
        self.runbooks_table = self.dynamodb.Table('ai-nutritionist-runbooks')
        self.escalations_table = self.dynamodb.Table('ai-nutritionist-escalations')
        
        # Configuration
        self.runbooks = self._load_runbooks()
        self.escalation_policies = self._load_escalation_policies()
        
        # Circuit breaker state
        self.circuit_breakers = {}
    
    def _load_runbooks(self) -> Dict[str, Runbook]:
        """Load automated response runbooks"""
        return {
            'high_error_rate': Runbook(
                name='High Error Rate Response',
                trigger_conditions={
                    'metric': 'ErrorRate',
                    'threshold': 10.0,
                    'duration': 300  # 5 minutes
                },
                automated_actions=[
                    ResponseAction.CIRCUIT_BREAKER,
                    ResponseAction.ALERT_TEAM,
                    ResponseAction.SCALE_OUT
                ],
                escalation_rules={
                    'immediate': ['oncall-engineer'],
                    '15_minutes': ['team-lead'],
                    '30_minutes': ['engineering-manager']
                },
                required_approvals=[],
                rollback_procedure=[
                    'Disable circuit breaker',
                    'Scale back to normal capacity',
                    'Monitor error rates'
                ]
            ),
            'database_performance': Runbook(
                name='Database Performance Issues',
                trigger_conditions={
                    'metric': 'DynamoDBThrottles',
                    'threshold': 5,
                    'duration': 300
                },
                automated_actions=[
                    ResponseAction.SCALE_OUT,
                    ResponseAction.ALERT_TEAM
                ],
                escalation_rules={
                    'immediate': ['database-team'],
                    '20_minutes': ['platform-team']
                },
                required_approvals=['database-lead'],
                rollback_procedure=[
                    'Revert capacity changes',
                    'Check for data consistency'
                ]
            ),
            'lambda_timeout': Runbook(
                name='Lambda Function Timeout',
                trigger_conditions={
                    'metric': 'LambdaDuration',
                    'threshold': 28000,  # 28 seconds
                    'duration': 600
                },
                automated_actions=[
                    ResponseAction.RESTART_SERVICE,
                    ResponseAction.ALERT_TEAM
                ],
                escalation_rules={
                    'immediate': ['backend-team'],
                    '10_minutes': ['oncall-engineer']
                },
                required_approvals=[],
                rollback_procedure=[
                    'Check lambda logs',
                    'Verify function configuration'
                ]
            ),
            'revenue_drop': Runbook(
                name='Revenue Drop Detection',
                trigger_conditions={
                    'metric': 'Revenue',
                    'threshold': 0.7,  # 30% drop
                    'duration': 1800   # 30 minutes
                },
                automated_actions=[
                    ResponseAction.ALERT_TEAM,
                    ResponseAction.CREATE_TICKET
                ],
                escalation_rules={
                    'immediate': ['business-team', 'product-manager'],
                    '30_minutes': ['ceo', 'cto']
                },
                required_approvals=[],
                rollback_procedure=[]
            )
        }
    
    def _load_escalation_policies(self) -> Dict[str, Dict[str, Any]]:
        """Load escalation policies"""
        return {
            'severity_mapping': {
                IncidentSeverity.SEV1: {
                    'response_time': 300,  # 5 minutes
                    'escalation_time': 900,  # 15 minutes
                    'notification_channels': ['pagerduty', 'phone', 'slack']
                },
                IncidentSeverity.SEV2: {
                    'response_time': 900,   # 15 minutes
                    'escalation_time': 1800,  # 30 minutes
                    'notification_channels': ['pagerduty', 'slack']
                },
                IncidentSeverity.SEV3: {
                    'response_time': 3600,  # 1 hour
                    'escalation_time': 7200,  # 2 hours
                    'notification_channels': ['slack', 'email']
                },
                IncidentSeverity.SEV4: {
                    'response_time': 14400,  # 4 hours
                    'escalation_time': 28800,  # 8 hours
                    'notification_channels': ['email']
                }
            },
            'teams': {
                'oncall-engineer': {
                    'slack_channel': '#oncall',
                    'pagerduty_service': 'P1234567',
                    'phone_numbers': ['+1234567890']
                },
                'backend-team': {
                    'slack_channel': '#backend',
                    'email_list': 'backend@ai-nutritionist.com'
                },
                'business-team': {
                    'slack_channel': '#business',
                    'email_list': 'business@ai-nutritionist.com'
                }
            }
        }
    
    async def detect_incident(self, metric_data: Dict[str, Any]) -> Optional[Incident]:
        """Detect if a metric breach constitutes an incident"""
        try:
            metric_name = metric_data.get('metric_name')
            current_value = metric_data.get('current_value')
            
            # Check each runbook for matching conditions
            for runbook_name, runbook in self.runbooks.items():
                if self._matches_trigger_conditions(metric_data, runbook.trigger_conditions):
                    # Create incident
                    incident = await self._create_incident(metric_data, runbook)
                    logger.info(f"Incident detected: {incident.id}")
                    return incident
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting incident: {e}")
            return None
    
    def _matches_trigger_conditions(self, metric_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Check if metric data matches trigger conditions"""
        metric_name = metric_data.get('metric_name', '').lower()
        current_value = metric_data.get('current_value', 0)
        
        # Simple condition matching
        if conditions.get('metric', '').lower() in metric_name:
            threshold = conditions.get('threshold', float('inf'))
            
            # For error rates and counts, check if exceeds threshold
            if 'error' in metric_name or 'throttle' in metric_name:
                return current_value >= threshold
            
            # For revenue, check if below threshold (percentage)
            if 'revenue' in metric_name:
                return current_value <= threshold
            
            # For duration/latency, check if exceeds threshold
            if 'duration' in metric_name or 'latency' in metric_name:
                return current_value >= threshold
        
        return False
    
    async def _create_incident(self, metric_data: Dict[str, Any], runbook: Runbook) -> Incident:
        """Create a new incident"""
        incident_id = f"INC-{int(datetime.utcnow().timestamp())}"
        now = datetime.utcnow()
        
        # Determine severity based on metric values
        severity = self._determine_severity(metric_data)
        
        incident = Incident(
            id=incident_id,
            title=f"{runbook.name} - {metric_data.get('metric_name')} threshold exceeded",
            description=f"Metric {metric_data.get('metric_name')} has value {metric_data.get('current_value')} which exceeds threshold {metric_data.get('threshold')}",
            severity=severity,
            status=IncidentStatus.DETECTED,
            affected_services=self._identify_affected_services(metric_data),
            root_cause=None,
            timeline=[{
                'timestamp': now.isoformat(),
                'event': 'Incident detected',
                'details': f"Triggered by {metric_data.get('metric_name')} metric"
            }],
            responders=[],
            created_at=now,
            updated_at=now,
            resolved_at=None,
            tags=metric_data.get('dimensions', {})
        )
        
        # Store incident
        await self._store_incident(incident)
        
        return incident
    
    def _determine_severity(self, metric_data: Dict[str, Any]) -> IncidentSeverity:
        """Determine incident severity based on metric data"""
        metric_name = metric_data.get('metric_name', '').lower()
        current_value = metric_data.get('current_value', 0)
        threshold = metric_data.get('threshold', 0)
        
        # Critical systems and high thresholds get higher severity
        if 'error' in metric_name and current_value >= 10:
            return IncidentSeverity.SEV1
        elif 'revenue' in metric_name and current_value <= 0.5:  # 50% drop
            return IncidentSeverity.SEV1
        elif 'duration' in metric_name and current_value >= 30000:  # 30 seconds
            return IncidentSeverity.SEV2
        elif current_value >= threshold * 2:  # Double the threshold
            return IncidentSeverity.SEV2
        elif current_value >= threshold * 1.5:  # 50% above threshold
            return IncidentSeverity.SEV3
        else:
            return IncidentSeverity.SEV4
    
    def _identify_affected_services(self, metric_data: Dict[str, Any]) -> List[str]:
        """Identify which services are affected by the incident"""
        dimensions = metric_data.get('dimensions', {})
        affected_services = []
        
        # Extract service information from dimensions
        if 'FunctionName' in dimensions:
            affected_services.append(f"Lambda: {dimensions['FunctionName']}")
        if 'TableName' in dimensions:
            affected_services.append(f"DynamoDB: {dimensions['TableName']}")
        if 'ApiName' in dimensions:
            affected_services.append(f"API Gateway: {dimensions['ApiName']}")
        
        return affected_services or ['Unknown Service']
    
    async def respond_to_incident(self, incident: Incident) -> Dict[str, Any]:
        """Execute automated response to incident"""
        response_results = {
            'incident_id': incident.id,
            'actions_taken': [],
            'escalations_sent': [],
            'success': False
        }
        
        try:
            # Get appropriate runbook
            runbook = self._get_runbook_for_incident(incident)
            if not runbook:
                logger.warning(f"No runbook found for incident {incident.id}")
                return response_results
            
            # Execute automated actions
            for action in runbook.automated_actions:
                try:
                    result = await self._execute_action(action, incident)
                    response_results['actions_taken'].append({
                        'action': action.value,
                        'result': result,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Failed to execute action {action.value}: {e}")
                    response_results['actions_taken'].append({
                        'action': action.value,
                        'result': f"Failed: {str(e)}",
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            # Send escalation notifications
            escalation_result = await self._handle_escalation(incident, runbook)
            response_results['escalations_sent'] = escalation_result
            
            # Update incident status
            incident.status = IncidentStatus.INVESTIGATING
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'event': 'Automated response executed',
                'details': f"Executed {len(runbook.automated_actions)} automated actions"
            })
            
            await self._update_incident(incident)
            
            response_results['success'] = True
            logger.info(f"Successfully responded to incident {incident.id}")
            
        except Exception as e:
            logger.error(f"Error responding to incident {incident.id}: {e}")
            response_results['error'] = str(e)
        
        return response_results
    
    def _get_runbook_for_incident(self, incident: Incident) -> Optional[Runbook]:
        """Get the appropriate runbook for an incident"""
        # Simple matching based on incident title
        for runbook_name, runbook in self.runbooks.items():
            if runbook_name.lower() in incident.title.lower():
                return runbook
        return None
    
    async def _execute_action(self, action: ResponseAction, incident: Incident) -> str:
        """Execute a specific automated action"""
        try:
            if action == ResponseAction.SCALE_OUT:
                return await self._scale_out_services(incident)
            elif action == ResponseAction.RESTART_SERVICE:
                return await self._restart_service(incident)
            elif action == ResponseAction.CIRCUIT_BREAKER:
                return await self._enable_circuit_breaker(incident)
            elif action == ResponseAction.FAILOVER:
                return await self._initiate_failover(incident)
            elif action == ResponseAction.ROLLBACK:
                return await self._initiate_rollback(incident)
            elif action == ResponseAction.ALERT_TEAM:
                return await self._alert_team(incident)
            elif action == ResponseAction.CREATE_TICKET:
                return await self._create_ticket(incident)
            else:
                return f"Unknown action: {action.value}"
        
        except Exception as e:
            return f"Action failed: {str(e)}"
    
    async def _scale_out_services(self, incident: Incident) -> str:
        """Scale out affected services"""
        try:
            results = []
            
            for service in incident.affected_services:
                if 'Lambda' in service:
                    # Increase lambda concurrency
                    function_name = service.split(': ')[1]
                    self.lambda_client.put_reserved_concurrency_configuration(
                        FunctionName=function_name,
                        ReservedConcurrencyLimit=100  # Increase from default
                    )
                    results.append(f"Scaled Lambda {function_name}")
                
                elif 'DynamoDB' in service:
                    # This would typically involve increasing read/write capacity
                    # For auto-scaling tables, we might adjust target utilization
                    table_name = service.split(': ')[1]
                    results.append(f"DynamoDB {table_name} scaling triggered")
            
            return "; ".join(results) if results else "No services scaled"
            
        except Exception as e:
            return f"Scale out failed: {str(e)}"
    
    async def _restart_service(self, incident: Incident) -> str:
        """Restart affected services"""
        try:
            results = []
            
            for service in incident.affected_services:
                if 'Lambda' in service:
                    function_name = service.split(': ')[1]
                    # Force new lambda execution environment
                    self.lambda_client.update_function_configuration(
                        FunctionName=function_name,
                        Environment={'Variables': {'RESTART_TIMESTAMP': str(int(time.time()))}}
                    )
                    results.append(f"Restarted Lambda {function_name}")
            
            return "; ".join(results) if results else "No services restarted"
            
        except Exception as e:
            return f"Restart failed: {str(e)}"
    
    async def _enable_circuit_breaker(self, incident: Incident) -> str:
        """Enable circuit breaker for affected services"""
        try:
            affected_service = incident.affected_services[0] if incident.affected_services else "unknown"
            self.circuit_breakers[affected_service] = {
                'enabled': True,
                'timestamp': datetime.utcnow(),
                'incident_id': incident.id
            }
            
            # Store circuit breaker state in Parameter Store
            self.ssm.put_parameter(
                Name=f'/ai-nutritionist/circuit-breaker/{affected_service}',
                Value='true',
                Type='String',
                Overwrite=True
            )
            
            return f"Circuit breaker enabled for {affected_service}"
            
        except Exception as e:
            return f"Circuit breaker failed: {str(e)}"
    
    async def _initiate_failover(self, incident: Incident) -> str:
        """Initiate failover procedures"""
        # This would implement failover to secondary regions or backup services
        return "Failover initiated (placeholder)"
    
    async def _initiate_rollback(self, incident: Incident) -> str:
        """Initiate rollback procedures"""
        # This would implement rollback to previous deployment
        return "Rollback initiated (placeholder)"
    
    async def _alert_team(self, incident: Incident) -> str:
        """Alert appropriate team members"""
        try:
            policy = self.escalation_policies['severity_mapping'][incident.severity]
            channels = policy['notification_channels']
            
            # Send alerts through configured channels
            alerts_sent = []
            
            if 'slack' in channels:
                # Send Slack notification (placeholder)
                alerts_sent.append("Slack")
            
            if 'pagerduty' in channels:
                # Send PagerDuty alert
                await self._send_pagerduty_incident(incident)
                alerts_sent.append("PagerDuty")
            
            if 'email' in channels:
                # Send email alert
                await self._send_email_alert(incident)
                alerts_sent.append("Email")
            
            return f"Alerts sent via: {', '.join(alerts_sent)}"
            
        except Exception as e:
            return f"Team alert failed: {str(e)}"
    
    async def _create_ticket(self, incident: Incident) -> str:
        """Create ticket in ticketing system"""
        # This would integrate with Jira, ServiceNow, etc.
        return f"Ticket created for incident {incident.id}"
    
    async def _handle_escalation(self, incident: Incident, runbook: Runbook) -> List[Dict[str, Any]]:
        """Handle escalation notifications"""
        escalations = []
        
        try:
            for timing, teams in runbook.escalation_rules.items():
                escalation = {
                    'timing': timing,
                    'teams': teams,
                    'scheduled_time': datetime.utcnow() + timedelta(
                        seconds=self._parse_timing(timing)
                    ),
                    'status': 'scheduled'
                }
                
                # Store escalation for later execution
                await self._schedule_escalation(incident.id, escalation)
                escalations.append(escalation)
        
        except Exception as e:
            logger.error(f"Error handling escalation: {e}")
        
        return escalations
    
    def _parse_timing(self, timing: str) -> int:
        """Parse timing string to seconds"""
        if timing == 'immediate':
            return 0
        elif timing.endswith('_minutes'):
            return int(timing.split('_')[0]) * 60
        elif timing.endswith('_hours'):
            return int(timing.split('_')[0]) * 3600
        else:
            return 0
    
    async def _send_pagerduty_incident(self, incident: Incident) -> bool:
        """Send incident to PagerDuty"""
        try:
            # PagerDuty API integration (placeholder)
            return True
        except Exception as e:
            logger.error(f"PagerDuty incident failed: {e}")
            return False
    
    async def _send_email_alert(self, incident: Incident) -> bool:
        """Send email alert"""
        try:
            # SNS email integration
            message = f"""
            Incident Alert: {incident.title}
            
            Severity: {incident.severity.value.upper()}
            Description: {incident.description}
            Affected Services: {', '.join(incident.affected_services)}
            Created: {incident.created_at.isoformat()}
            
            Incident ID: {incident.id}
            """
            
            self.sns.publish(
                TopicArn='arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-alerts',
                Message=message,
                Subject=f"[{incident.severity.value.upper()}] {incident.title}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
            return False
    
    async def _store_incident(self, incident: Incident) -> bool:
        """Store incident in DynamoDB"""
        try:
            self.incidents_table.put_item(
                Item={
                    'incident_id': incident.id,
                    'title': incident.title,
                    'description': incident.description,
                    'severity': incident.severity.value,
                    'status': incident.status.value,
                    'affected_services': incident.affected_services,
                    'root_cause': incident.root_cause,
                    'timeline': incident.timeline,
                    'responders': incident.responders,
                    'created_at': incident.created_at.isoformat(),
                    'updated_at': incident.updated_at.isoformat(),
                    'resolved_at': incident.resolved_at.isoformat() if incident.resolved_at else None,
                    'tags': incident.tags
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error storing incident: {e}")
            return False
    
    async def _update_incident(self, incident: Incident) -> bool:
        """Update incident in DynamoDB"""
        try:
            incident.updated_at = datetime.utcnow()
            
            self.incidents_table.update_item(
                Key={'incident_id': incident.id},
                UpdateExpression='SET #status = :status, timeline = :timeline, updated_at = :updated_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': incident.status.value,
                    ':timeline': incident.timeline,
                    ':updated_at': incident.updated_at.isoformat()
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating incident: {e}")
            return False
    
    async def _schedule_escalation(self, incident_id: str, escalation: Dict[str, Any]) -> bool:
        """Schedule escalation for later execution"""
        try:
            self.escalations_table.put_item(
                Item={
                    'escalation_id': f"{incident_id}-{escalation['timing']}",
                    'incident_id': incident_id,
                    'timing': escalation['timing'],
                    'teams': escalation['teams'],
                    'scheduled_time': escalation['scheduled_time'].isoformat(),
                    'status': escalation['status'],
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling escalation: {e}")
            return False
    
    async def process_escalations(self) -> Dict[str, Any]:
        """Process pending escalations"""
        results = {
            'processed': 0,
            'failed': 0,
            'success': True
        }
        
        try:
            # Query pending escalations
            now = datetime.utcnow()
            
            # This would scan for escalations that are due
            # Implementation would depend on DynamoDB table design
            
            results['processed'] = 0  # Placeholder
            
        except Exception as e:
            logger.error(f"Error processing escalations: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results


# Lambda handler for processing incidents
async def incident_handler(event, context):
    """Lambda handler for incident processing"""
    incident_service = IncidentResponseService()
    
    try:
        # Parse event data
        if 'Records' in event:
            # SNS/SQS triggered
            for record in event['Records']:
                if 'Sns' in record:
                    message = json.loads(record['Sns']['Message'])
                    incident = await incident_service.detect_incident(message)
                    
                    if incident:
                        response = await incident_service.respond_to_incident(incident)
                        logger.info(f"Incident response: {response}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Incident processing completed'})
        }
        
    except Exception as e:
        logger.error(f"Error in incident handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        service = IncidentResponseService()
        
        # Test incident detection
        test_metric = {
            'metric_name': 'ErrorRate',
            'current_value': 15.0,
            'threshold': 10.0,
            'dimensions': {'FunctionName': 'ai-nutritionist-message-handler'}
        }
        
        incident = await service.detect_incident(test_metric)
        if incident:
            response = await service.respond_to_incident(incident)
            print(json.dumps(response, indent=2))
    
    asyncio.run(main())
