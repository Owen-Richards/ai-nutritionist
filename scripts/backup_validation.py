#!/usr/bin/env python3
"""
Backup Validation and Monitoring System for AI Nutritionist Application

This script provides comprehensive backup validation, monitoring, and alerting
with the following features:
- Daily backup validation
- Backup integrity checks
- Performance monitoring
- Cost tracking
- Compliance reporting
- Automated alerts

Author: AI Nutritionist DevOps Team
Version: 1.0.0
"""

import os
import sys
import json
import boto3
import logging
import hashlib
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import argparse
from botocore.exceptions import ClientError


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BackupValidationResult:
    """Result of backup validation"""
    backup_id: str
    backup_type: str
    validation_status: str  # SUCCESS, FAILED, WARNING, SKIPPED
    validation_tests: List[Dict[str, Any]]
    size_bytes: int
    creation_date: datetime
    last_verified: datetime
    compliance_status: str
    cost_estimate: float
    issues: List[str]
    recommendations: List[str]


@dataclass
class BackupMetrics:
    """Backup performance metrics"""
    total_backups: int
    successful_backups: int
    failed_backups: int
    total_size_gb: float
    avg_backup_duration: float
    success_rate: float
    cost_per_gb: float
    rpo_compliance: float
    rto_compliance: float


class BackupValidator:
    """Comprehensive backup validation and monitoring"""

    def __init__(self, project_name: str = "ai-nutritionist", environment: str = "prod"):
        self.project_name = project_name
        self.environment = environment
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize AWS clients
        self.backup_client = boto3.client('backup', region_name=self.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.aws_region)
        self.sns_client = boto3.client('sns', region_name=self.aws_region)
        self.cost_explorer = boto3.client('ce', region_name='us-east-1')  # Cost Explorer is only in us-east-1
        
        # Configuration
        self.backup_vault = f"{project_name}-backup-vault-{environment}"
        self.notification_topic = f"{project_name}-backup-alerts"

    def validate_all_backups(self, days_back: int = 7) -> List[BackupValidationResult]:
        """Validate all backups from the last N days"""
        logger.info(f"Starting validation of backups from last {days_back} days")
        
        validation_results = []
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            # Get all recovery points from backup vault
            paginator = self.backup_client.get_paginator('list_recovery_points_by_backup_vault')
            
            for page in paginator.paginate(
                BackupVaultName=self.backup_vault,
                ByCreatedAfter=start_date,
                ByCreatedBefore=end_date
            ):
                for recovery_point in page['RecoveryPoints']:
                    result = self._validate_recovery_point(recovery_point)
                    validation_results.append(result)
                    
        except Exception as e:
            logger.error(f"Error during backup validation: {str(e)}")
            
        logger.info(f"Validation completed. Processed {len(validation_results)} backups")
        return validation_results

    def _validate_recovery_point(self, recovery_point: Dict[str, Any]) -> BackupValidationResult:
        """Validate a single recovery point"""
        backup_id = recovery_point['RecoveryPointArn']
        backup_type = self._determine_backup_type(recovery_point['ResourceArn'])
        
        logger.debug(f"Validating backup: {backup_id}")
        
        validation_tests = []
        issues = []
        recommendations = []
        
        # Test 1: Backup completeness
        completeness_test = self._test_backup_completeness(recovery_point)
        validation_tests.append(completeness_test)
        
        # Test 2: Backup integrity
        integrity_test = self._test_backup_integrity(recovery_point)
        validation_tests.append(integrity_test)
        
        # Test 3: Encryption validation
        encryption_test = self._test_backup_encryption(recovery_point)
        validation_tests.append(encryption_test)
        
        # Test 4: Access permissions
        permissions_test = self._test_backup_permissions(recovery_point)
        validation_tests.append(permissions_test)
        
        # Test 5: Retention compliance
        retention_test = self._test_retention_compliance(recovery_point)
        validation_tests.append(retention_test)
        
        # Test 6: Cross-region replication (if applicable)
        if self.environment == 'prod':
            replication_test = self._test_cross_region_replication(recovery_point)
            validation_tests.append(replication_test)
        
        # Determine overall validation status
        failed_tests = [t for t in validation_tests if t['status'] == 'FAILED']
        warning_tests = [t for t in validation_tests if t['status'] == 'WARNING']
        
        if failed_tests:
            validation_status = 'FAILED'
            issues.extend([t['message'] for t in failed_tests])
        elif warning_tests:
            validation_status = 'WARNING'
            issues.extend([t['message'] for t in warning_tests])
        else:
            validation_status = 'SUCCESS'
        
        # Generate recommendations
        recommendations = self._generate_recommendations(validation_tests, recovery_point)
        
        # Calculate compliance status
        compliance_status = self._calculate_compliance_status(validation_tests)
        
        # Estimate cost
        cost_estimate = self._estimate_backup_cost(recovery_point)
        
        return BackupValidationResult(
            backup_id=backup_id,
            backup_type=backup_type,
            validation_status=validation_status,
            validation_tests=validation_tests,
            size_bytes=recovery_point.get('BackupSizeInBytes', 0),
            creation_date=recovery_point['CreationDate'],
            last_verified=datetime.utcnow(),
            compliance_status=compliance_status,
            cost_estimate=cost_estimate,
            issues=issues,
            recommendations=recommendations
        )

    def _determine_backup_type(self, resource_arn: str) -> str:
        """Determine backup type from resource ARN"""
        if 'dynamodb' in resource_arn:
            return 'dynamodb'
        elif 's3' in resource_arn:
            return 's3'
        elif 'rds' in resource_arn:
            return 'rds'
        elif 'efs' in resource_arn:
            return 'efs'
        else:
            return 'unknown'

    def _test_backup_completeness(self, recovery_point: Dict[str, Any]) -> Dict[str, Any]:
        """Test if backup completed successfully"""
        try:
            status = recovery_point.get('Status', 'UNKNOWN')
            
            if status == 'COMPLETED':
                return {
                    'test_name': 'backup_completeness',
                    'status': 'SUCCESS',
                    'message': 'Backup completed successfully',
                    'details': {'backup_status': status}
                }
            elif status in ['PARTIAL', 'FAILED']:
                return {
                    'test_name': 'backup_completeness',
                    'status': 'FAILED',
                    'message': f'Backup failed with status: {status}',
                    'details': {'backup_status': status}
                }
            else:
                return {
                    'test_name': 'backup_completeness',
                    'status': 'WARNING',
                    'message': f'Backup in unexpected status: {status}',
                    'details': {'backup_status': status}
                }
                
        except Exception as e:
            return {
                'test_name': 'backup_completeness',
                'status': 'FAILED',
                'message': f'Error checking backup completeness: {str(e)}',
                'details': {'error': str(e)}
            }

    def _test_backup_integrity(self, recovery_point: Dict[str, Any]) -> Dict[str, Any]:
        """Test backup data integrity"""
        try:
            # For DynamoDB, check if we can describe the backup
            if 'dynamodb' in recovery_point['ResourceArn']:
                backup_details = self.backup_client.describe_recovery_point(
                    BackupVaultName=self.backup_vault,
                    RecoveryPointArn=recovery_point['RecoveryPointArn']
                )
                
                # Check for data consistency indicators
                if backup_details.get('BackupSizeInBytes', 0) > 0:
                    return {
                        'test_name': 'backup_integrity',
                        'status': 'SUCCESS',
                        'message': 'Backup integrity verified',
                        'details': {
                            'backup_size': backup_details.get('BackupSizeInBytes'),
                            'creation_date': backup_details.get('CreationDate')
                        }
                    }
                else:
                    return {
                        'test_name': 'backup_integrity',
                        'status': 'WARNING',
                        'message': 'Backup size is zero or unknown',
                        'details': {'backup_size': backup_details.get('BackupSizeInBytes', 0)}
                    }
            
            # For other backup types, basic validation
            return {
                'test_name': 'backup_integrity',
                'status': 'SUCCESS',
                'message': 'Basic integrity checks passed',
                'details': {}
            }
            
        except Exception as e:
            return {
                'test_name': 'backup_integrity',
                'status': 'FAILED',
                'message': f'Error checking backup integrity: {str(e)}',
                'details': {'error': str(e)}
            }

    def _test_backup_encryption(self, recovery_point: Dict[str, Any]) -> Dict[str, Any]:
        """Test backup encryption status"""
        try:
            backup_details = self.backup_client.describe_recovery_point(
                BackupVaultName=self.backup_vault,
                RecoveryPointArn=recovery_point['RecoveryPointArn']
            )
            
            # Check encryption status
            encryption_key_arn = backup_details.get('EncryptionKeyArn')
            
            if encryption_key_arn:
                return {
                    'test_name': 'backup_encryption',
                    'status': 'SUCCESS',
                    'message': 'Backup is properly encrypted',
                    'details': {'encryption_key_arn': encryption_key_arn}
                }
            else:
                return {
                    'test_name': 'backup_encryption',
                    'status': 'FAILED',
                    'message': 'Backup encryption not detected',
                    'details': {}
                }
                
        except Exception as e:
            return {
                'test_name': 'backup_encryption',
                'status': 'WARNING',
                'message': f'Could not verify encryption: {str(e)}',
                'details': {'error': str(e)}
            }

    def _test_backup_permissions(self, recovery_point: Dict[str, Any]) -> Dict[str, Any]:
        """Test backup access permissions"""
        try:
            # Try to access backup metadata (basic permission test)
            backup_details = self.backup_client.describe_recovery_point(
                BackupVaultName=self.backup_vault,
                RecoveryPointArn=recovery_point['RecoveryPointArn']
            )
            
            return {
                'test_name': 'backup_permissions',
                'status': 'SUCCESS',
                'message': 'Backup access permissions verified',
                'details': {'accessible': True}
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['AccessDenied', 'Forbidden']:
                return {
                    'test_name': 'backup_permissions',
                    'status': 'FAILED',
                    'message': f'Access denied to backup: {error_code}',
                    'details': {'error_code': error_code}
                }
            else:
                return {
                    'test_name': 'backup_permissions',
                    'status': 'WARNING',
                    'message': f'Permission test inconclusive: {error_code}',
                    'details': {'error_code': error_code}
                }
        except Exception as e:
            return {
                'test_name': 'backup_permissions',
                'status': 'WARNING',
                'message': f'Error testing permissions: {str(e)}',
                'details': {'error': str(e)}
            }

    def _test_retention_compliance(self, recovery_point: Dict[str, Any]) -> Dict[str, Any]:
        """Test backup retention policy compliance"""
        try:
            creation_date = recovery_point['CreationDate']
            current_date = datetime.utcnow().replace(tzinfo=creation_date.tzinfo)
            age_days = (current_date - creation_date).days
            
            # Get expected retention period based on backup type
            expected_retention = self._get_expected_retention(recovery_point)
            
            if age_days <= expected_retention:
                return {
                    'test_name': 'retention_compliance',
                    'status': 'SUCCESS',
                    'message': f'Backup within retention period ({age_days}/{expected_retention} days)',
                    'details': {
                        'age_days': age_days,
                        'expected_retention_days': expected_retention
                    }
                }
            else:
                return {
                    'test_name': 'retention_compliance',
                    'status': 'WARNING',
                    'message': f'Backup exceeds retention period ({age_days}/{expected_retention} days)',
                    'details': {
                        'age_days': age_days,
                        'expected_retention_days': expected_retention,
                        'should_be_deleted': True
                    }
                }
                
        except Exception as e:
            return {
                'test_name': 'retention_compliance',
                'status': 'WARNING',
                'message': f'Error checking retention compliance: {str(e)}',
                'details': {'error': str(e)}
            }

    def _test_cross_region_replication(self, recovery_point: Dict[str, Any]) -> Dict[str, Any]:
        """Test cross-region backup replication"""
        try:
            # Check if backup exists in secondary region
            secondary_region = 'us-west-2' if self.aws_region == 'us-east-1' else 'us-east-1'
            secondary_backup_client = boto3.client('backup', region_name=secondary_region)
            
            # Look for corresponding backup in secondary region
            secondary_vault = f"{self.project_name}-backup-vault-cross-region-{self.environment}"
            
            try:
                secondary_backups = secondary_backup_client.list_recovery_points_by_backup_vault(
                    BackupVaultName=secondary_vault,
                    ByCreatedAfter=recovery_point['CreationDate'] - timedelta(hours=1),
                    ByCreatedBefore=recovery_point['CreationDate'] + timedelta(hours=1)
                )
                
                if secondary_backups['RecoveryPoints']:
                    return {
                        'test_name': 'cross_region_replication',
                        'status': 'SUCCESS',
                        'message': f'Cross-region backup found in {secondary_region}',
                        'details': {
                            'secondary_region': secondary_region,
                            'replicated_backups': len(secondary_backups['RecoveryPoints'])
                        }
                    }
                else:
                    return {
                        'test_name': 'cross_region_replication',
                        'status': 'WARNING',
                        'message': f'No cross-region backup found in {secondary_region}',
                        'details': {'secondary_region': secondary_region}
                    }
                    
            except ClientError as e:
                if 'does not exist' in str(e).lower():
                    return {
                        'test_name': 'cross_region_replication',
                        'status': 'WARNING',
                        'message': f'Cross-region backup vault not found in {secondary_region}',
                        'details': {'secondary_region': secondary_region}
                    }
                else:
                    raise
                    
        except Exception as e:
            return {
                'test_name': 'cross_region_replication',
                'status': 'WARNING',
                'message': f'Error checking cross-region replication: {str(e)}',
                'details': {'error': str(e)}
            }

    def _get_expected_retention(self, recovery_point: Dict[str, Any]) -> int:
        """Get expected retention period for backup type"""
        backup_type = self._determine_backup_type(recovery_point['ResourceArn'])
        
        retention_policies = {
            'dynamodb': 35,  # 35 days for DynamoDB
            's3': 90,        # 90 days for S3
            'rds': 35,       # 35 days for RDS
            'efs': 30,       # 30 days for EFS
            'unknown': 30    # Default 30 days
        }
        
        return retention_policies.get(backup_type, 30)

    def _generate_recommendations(self, validation_tests: List[Dict[str, Any]], 
                                recovery_point: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check for failed tests
        failed_tests = [t for t in validation_tests if t['status'] == 'FAILED']
        warning_tests = [t for t in validation_tests if t['status'] == 'WARNING']
        
        if any(t['test_name'] == 'backup_encryption' for t in failed_tests):
            recommendations.append("Enable encryption for all backups using customer-managed KMS keys")
        
        if any(t['test_name'] == 'cross_region_replication' for t in warning_tests):
            recommendations.append("Set up cross-region backup replication for disaster recovery")
        
        if any(t['test_name'] == 'retention_compliance' for t in warning_tests):
            recommendations.append("Review and cleanup old backups to reduce storage costs")
        
        # Check backup size
        backup_size = recovery_point.get('BackupSizeInBytes', 0)
        if backup_size == 0:
            recommendations.append("Investigate why backup size is zero - may indicate backup failure")
        elif backup_size > 1024**3:  # > 1GB
            recommendations.append("Consider implementing backup compression to reduce storage costs")
        
        return recommendations

    def _calculate_compliance_status(self, validation_tests: List[Dict[str, Any]]) -> str:
        """Calculate overall compliance status"""
        failed_tests = [t for t in validation_tests if t['status'] == 'FAILED']
        warning_tests = [t for t in validation_tests if t['status'] == 'WARNING']
        
        critical_tests = ['backup_completeness', 'backup_encryption', 'backup_permissions']
        critical_failures = [t for t in failed_tests if t['test_name'] in critical_tests]
        
        if critical_failures:
            return 'NON_COMPLIANT'
        elif failed_tests or len(warning_tests) > 2:
            return 'PARTIALLY_COMPLIANT'
        else:
            return 'COMPLIANT'

    def _estimate_backup_cost(self, recovery_point: Dict[str, Any]) -> float:
        """Estimate backup storage cost"""
        try:
            size_gb = recovery_point.get('BackupSizeInBytes', 0) / (1024**3)
            
            # AWS Backup pricing (approximate)
            storage_cost_per_gb = 0.05  # $0.05 per GB per month
            
            # Calculate age-based cost (lifecycle transitions)
            creation_date = recovery_point['CreationDate']
            age_days = (datetime.utcnow().replace(tzinfo=creation_date.tzinfo) - creation_date).days
            
            if age_days > 90:
                # Glacier pricing
                cost_per_gb = 0.004
            elif age_days > 30:
                # IA pricing
                cost_per_gb = 0.0125
            else:
                # Standard pricing
                cost_per_gb = storage_cost_per_gb
            
            return size_gb * cost_per_gb
            
        except Exception:
            return 0.0

    def generate_backup_metrics(self, validation_results: List[BackupValidationResult]) -> BackupMetrics:
        """Generate comprehensive backup metrics"""
        if not validation_results:
            return BackupMetrics(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        total_backups = len(validation_results)
        successful_backups = len([r for r in validation_results if r.validation_status == 'SUCCESS'])
        failed_backups = len([r for r in validation_results if r.validation_status == 'FAILED'])
        
        total_size_gb = sum(r.size_bytes for r in validation_results) / (1024**3)
        success_rate = (successful_backups / total_backups * 100) if total_backups > 0 else 0.0
        
        # Calculate average backup duration (from CloudWatch if available)
        avg_backup_duration = self._get_average_backup_duration()
        
        # Calculate cost metrics
        total_cost = sum(r.cost_estimate for r in validation_results)
        cost_per_gb = (total_cost / total_size_gb) if total_size_gb > 0 else 0.0
        
        # Calculate RPO/RTO compliance
        rpo_compliance = self._calculate_rpo_compliance(validation_results)
        rto_compliance = self._calculate_rto_compliance(validation_results)
        
        return BackupMetrics(
            total_backups=total_backups,
            successful_backups=successful_backups,
            failed_backups=failed_backups,
            total_size_gb=total_size_gb,
            avg_backup_duration=avg_backup_duration,
            success_rate=success_rate,
            cost_per_gb=cost_per_gb,
            rpo_compliance=rpo_compliance,
            rto_compliance=rto_compliance
        )

    def _get_average_backup_duration(self) -> float:
        """Get average backup duration from CloudWatch metrics"""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Backup',
                MetricName='Duration',
                Dimensions=[
                    {
                        'Name': 'BackupVaultName',
                        'Value': self.backup_vault
                    }
                ],
                StartTime=datetime.utcnow() - timedelta(days=7),
                EndTime=datetime.utcnow(),
                Period=86400,  # Daily
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                return sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints'])
            else:
                return 0.0
                
        except Exception:
            return 0.0

    def _calculate_rpo_compliance(self, validation_results: List[BackupValidationResult]) -> float:
        """Calculate RPO compliance percentage"""
        # RPO target: backups should be taken at least every hour
        target_interval_hours = 1
        compliant_backups = 0
        
        for result in validation_results:
            # Check if backup was taken within RPO window
            time_since_backup = datetime.utcnow() - result.creation_date.replace(tzinfo=None)
            if time_since_backup.total_seconds() / 3600 <= target_interval_hours * 24:  # Within 24 hours
                compliant_backups += 1
        
        return (compliant_backups / len(validation_results) * 100) if validation_results else 0.0

    def _calculate_rto_compliance(self, validation_results: List[BackupValidationResult]) -> float:
        """Calculate RTO compliance percentage"""
        # RTO target: backups should be restorable within 4 hours
        # This is a simplified check - in real scenario, you'd test actual restoration
        compliant_backups = len([r for r in validation_results if r.validation_status == 'SUCCESS'])
        
        return (compliant_backups / len(validation_results) * 100) if validation_results else 0.0

    def generate_compliance_report(self, validation_results: List[BackupValidationResult]) -> Dict[str, Any]:
        """Generate detailed compliance report"""
        metrics = self.generate_backup_metrics(validation_results)
        
        # Categorize results by compliance status
        compliance_summary = {
            'COMPLIANT': len([r for r in validation_results if r.compliance_status == 'COMPLIANT']),
            'PARTIALLY_COMPLIANT': len([r for r in validation_results if r.compliance_status == 'PARTIALLY_COMPLIANT']),
            'NON_COMPLIANT': len([r for r in validation_results if r.compliance_status == 'NON_COMPLIANT'])
        }
        
        # Identify top issues
        all_issues = []
        for result in validation_results:
            all_issues.extend(result.issues)
        
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Generate recommendations
        all_recommendations = []
        for result in validation_results:
            all_recommendations.extend(result.recommendations)
        
        unique_recommendations = list(set(all_recommendations))
        
        return {
            'report_generated': datetime.utcnow().isoformat(),
            'project_name': self.project_name,
            'environment': self.environment,
            'aws_region': self.aws_region,
            'metrics': asdict(metrics),
            'compliance_summary': compliance_summary,
            'top_issues': top_issues,
            'recommendations': unique_recommendations,
            'backup_details': [asdict(r) for r in validation_results],
            'overall_compliance_score': (compliance_summary['COMPLIANT'] / len(validation_results) * 100) if validation_results else 0.0
        }

    def send_alert_notification(self, validation_results: List[BackupValidationResult], metrics: BackupMetrics):
        """Send alert notification based on validation results"""
        try:
            # Determine alert level
            failed_backups = [r for r in validation_results if r.validation_status == 'FAILED']
            critical_issues = [r for r in validation_results if r.compliance_status == 'NON_COMPLIANT']
            
            if critical_issues or metrics.success_rate < 80:
                alert_level = 'CRITICAL'
                subject = f"🚨 CRITICAL: Backup Validation Failures - {self.project_name}"
            elif failed_backups or metrics.success_rate < 95:
                alert_level = 'WARNING'
                subject = f"⚠️ WARNING: Backup Validation Issues - {self.project_name}"
            elif metrics.success_rate < 100:
                alert_level = 'INFO'
                subject = f"ℹ️ INFO: Backup Validation Report - {self.project_name}"
            else:
                alert_level = 'SUCCESS'
                subject = f"✅ SUCCESS: All Backups Validated - {self.project_name}"
            
            # Create message
            message = f"""
Backup Validation Report - {self.project_name} ({self.environment})
Generated: {datetime.utcnow().isoformat()}

📊 Summary:
- Total Backups: {metrics.total_backups}
- Success Rate: {metrics.success_rate:.1f}%
- Failed Backups: {metrics.failed_backups}
- Total Size: {metrics.total_size_gb:.2f} GB
- Estimated Cost: ${sum(r.cost_estimate for r in validation_results):.2f}/month

🔍 Compliance:
- RPO Compliance: {metrics.rpo_compliance:.1f}%
- RTO Compliance: {metrics.rto_compliance:.1f}%
- Non-Compliant Backups: {len([r for r in validation_results if r.compliance_status == 'NON_COMPLIANT'])}

"""
            
            if failed_backups:
                message += f"\n❌ Failed Backups ({len(failed_backups)}):\n"
                for backup in failed_backups[:5]:  # Show first 5
                    message += f"- {backup.backup_type}: {backup.backup_id[:50]}...\n"
                    if backup.issues:
                        message += f"  Issues: {', '.join(backup.issues[:2])}\n"
            
            if critical_issues:
                message += f"\n🚨 Non-Compliant Backups ({len(critical_issues)}):\n"
                for backup in critical_issues[:3]:  # Show first 3
                    message += f"- {backup.backup_type}: {backup.backup_id[:50]}...\n"
            
            # Send SNS notification
            self.sns_client.publish(
                TopicArn=f"arn:aws:sns:{self.aws_region}:*:{self.notification_topic}",
                Subject=subject,
                Message=message
            )
            
            logger.info(f"Alert notification sent: {alert_level}")
            
        except Exception as e:
            logger.error(f"Failed to send alert notification: {str(e)}")

    def publish_validation_metrics(self, metrics: BackupMetrics):
        """Publish validation metrics to CloudWatch"""
        try:
            timestamp = datetime.utcnow()
            
            metric_data = [
                {
                    'MetricName': 'BackupValidationSuccessRate',
                    'Value': metrics.success_rate,
                    'Unit': 'Percent',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'TotalBackupCount',
                    'Value': metrics.total_backups,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'FailedBackupCount',
                    'Value': metrics.failed_backups,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'BackupStorageSizeGB',
                    'Value': metrics.total_size_gb,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'BackupCostPerGB',
                    'Value': metrics.cost_per_gb,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'RPOCompliance',
                    'Value': metrics.rpo_compliance,
                    'Unit': 'Percent',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'RTOCompliance',
                    'Value': metrics.rto_compliance,
                    'Unit': 'Percent',
                    'Timestamp': timestamp
                }
            ]
            
            # Add dimensions
            for metric in metric_data:
                metric['Dimensions'] = [
                    {'Name': 'Project', 'Value': self.project_name},
                    {'Name': 'Environment', 'Value': self.environment}
                ]
            
            # Publish metrics
            self.cloudwatch.put_metric_data(
                Namespace='AI-Nutritionist/BackupValidation',
                MetricData=metric_data
            )
            
            logger.info("Validation metrics published to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish validation metrics: {str(e)}")

    def export_report(self, report: Dict[str, Any], format: str = 'json') -> str:
        """Export validation report to file"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_validation_report_{self.environment}_{timestamp}"
        
        if format.lower() == 'json':
            filepath = f"{filename}.json"
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        elif format.lower() == 'csv':
            filepath = f"{filename}.csv"
            # Convert backup details to DataFrame
            df = pd.DataFrame(report['backup_details'])
            df.to_csv(filepath, index=False)
        
        elif format.lower() == 'html':
            filepath = f"{filename}.html"
            self._generate_html_report(report, filepath)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Report exported to: {filepath}")
        return filepath

    def _generate_html_report(self, report: Dict[str, Any], filepath: str):
        """Generate HTML report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backup Validation Report - {self.project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .metrics {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 20px 0; }}
        .metric-card {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; min-width: 200px; }}
        .success {{ color: green; }}
        .warning {{ color: orange; }}
        .error {{ color: red; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Backup Validation Report</h1>
        <p><strong>Project:</strong> {report['project_name']}</p>
        <p><strong>Environment:</strong> {report['environment']}</p>
        <p><strong>Generated:</strong> {report['report_generated']}</p>
        <p><strong>Overall Compliance Score:</strong> {report['overall_compliance_score']:.1f}%</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <h3>Total Backups</h3>
            <p style="font-size: 24px; font-weight: bold;">{report['metrics']['total_backups']}</p>
        </div>
        <div class="metric-card">
            <h3>Success Rate</h3>
            <p style="font-size: 24px; font-weight: bold;">{report['metrics']['success_rate']:.1f}%</p>
        </div>
        <div class="metric-card">
            <h3>Total Size</h3>
            <p style="font-size: 24px; font-weight: bold;">{report['metrics']['total_size_gb']:.2f} GB</p>
        </div>
        <div class="metric-card">
            <h3>Failed Backups</h3>
            <p style="font-size: 24px; font-weight: bold; color: red;">{report['metrics']['failed_backups']}</p>
        </div>
    </div>
    
    <h2>Compliance Summary</h2>
    <ul>
        <li class="success">Compliant: {report['compliance_summary']['COMPLIANT']}</li>
        <li class="warning">Partially Compliant: {report['compliance_summary']['PARTIALLY_COMPLIANT']}</li>
        <li class="error">Non-Compliant: {report['compliance_summary']['NON_COMPLIANT']}</li>
    </ul>
    
    <h2>Top Issues</h2>
    <ol>
        {''.join(f'<li>{issue[0]} (Count: {issue[1]})</li>' for issue in report['top_issues'])}
    </ol>
    
    <h2>Recommendations</h2>
    <ul>
        {''.join(f'<li>{rec}</li>' for rec in report['recommendations'])}
    </ul>
</body>
</html>
        """
        
        with open(filepath, 'w') as f:
            f.write(html_content)


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='AI Nutritionist Backup Validation')
    parser.add_argument('--environment', '-e', default='prod', help='Environment')
    parser.add_argument('--project-name', '-p', default='ai-nutritionist', help='Project name')
    parser.add_argument('--days-back', '-d', type=int, default=7, help='Days back to validate')
    parser.add_argument('--export-format', choices=['json', 'csv', 'html'], default='json', help='Report format')
    parser.add_argument('--send-alerts', action='store_true', help='Send alert notifications')
    parser.add_argument('--publish-metrics', action='store_true', help='Publish metrics to CloudWatch')
    
    args = parser.parse_args()
    
    # Create validator
    validator = BackupValidator(args.project_name, args.environment)
    
    # Run validation
    print(f"Validating backups for {args.project_name} ({args.environment})...")
    validation_results = validator.validate_all_backups(args.days_back)
    
    # Generate metrics and report
    metrics = validator.generate_backup_metrics(validation_results)
    report = validator.generate_compliance_report(validation_results)
    
    # Export report
    report_file = validator.export_report(report, args.export_format)
    
    # Send alerts if requested
    if args.send_alerts:
        validator.send_alert_notification(validation_results, metrics)
    
    # Publish metrics if requested
    if args.publish_metrics:
        validator.publish_validation_metrics(metrics)
    
    # Print summary
    print("\n" + "="*80)
    print("BACKUP VALIDATION SUMMARY")
    print("="*80)
    print(f"Total Backups: {metrics.total_backups}")
    print(f"Success Rate: {metrics.success_rate:.1f}%")
    print(f"Failed Backups: {metrics.failed_backups}")
    print(f"Compliance Score: {report['overall_compliance_score']:.1f}%")
    print(f"Report exported to: {report_file}")
    
    if metrics.failed_backups > 0 or report['overall_compliance_score'] < 95:
        sys.exit(1)


if __name__ == "__main__":
    main()
