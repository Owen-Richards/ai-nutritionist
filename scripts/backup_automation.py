#!/usr/bin/env python3
"""
Comprehensive Backup Automation System for AI Nutritionist Application

This script provides automated backup functionality with the following features:
- Database backups (DynamoDB)
- File storage backups (S3)
- Configuration backups
- Code repository backups
- Cross-region replication
- Backup verification
- Recovery procedures
- Monitoring and alerting

Author: AI Nutritionist DevOps Team
Version: 1.0.0
Last Updated: October 14, 2025
"""

import os
import sys
import json
import boto3
import logging
import hashlib
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from botocore.exceptions import ClientError, BotoCoreError
import argparse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/backup-automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class BackupConfig:
    """Configuration for backup operations"""
    project_name: str = "ai-nutritionist"
    environment: str = "prod"
    aws_region: str = "us-east-1"
    backup_region: str = "us-west-2"
    backup_vault: str = "ai-nutritionist-backup-vault-prod"
    retention_days: int = 35
    rto_hours: int = 4
    rpo_hours: int = 1
    enable_cross_region: bool = True
    enable_encryption: bool = True
    notification_sns_topic: str = "ai-nutritionist-backup-alerts"


@dataclass
class BackupResult:
    """Result of a backup operation"""
    success: bool
    backup_id: str
    size_bytes: int
    duration_seconds: float
    error_message: Optional[str] = None
    backup_type: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BackupAutomation:
    """Main backup automation class"""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.session = boto3.Session()
        
        # Initialize AWS clients
        self.backup_client = self.session.client('backup', region_name=config.aws_region)
        self.dynamodb = self.session.resource('dynamodb', region_name=config.aws_region)
        self.s3_client = self.session.client('s3', region_name=config.aws_region)
        self.ssm_client = self.session.client('ssm', region_name=config.aws_region)
        self.sns_client = self.session.client('sns', region_name=config.aws_region)
        self.cloudwatch = self.session.client('cloudwatch', region_name=config.aws_region)
        
        # Cross-region clients
        if config.enable_cross_region:
            self.backup_client_dr = self.session.client('backup', region_name=config.backup_region)
            self.s3_client_dr = self.session.client('s3', region_name=config.backup_region)

    def backup_dynamodb_tables(self) -> List[BackupResult]:
        """Backup all DynamoDB tables"""
        logger.info("Starting DynamoDB backup process")
        results = []
        
        try:
            # Get list of tables to backup
            tables = self._get_application_tables()
            
            for table_name in tables:
                result = self._backup_dynamodb_table(table_name)
                results.append(result)
                
                if result.success:
                    logger.info(f"Successfully backed up table: {table_name}")
                else:
                    logger.error(f"Failed to backup table {table_name}: {result.error_message}")
                    
        except Exception as e:
            logger.error(f"Error during DynamoDB backup: {str(e)}")
            results.append(BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=0,
                error_message=str(e),
                backup_type="dynamodb"
            ))
            
        return results

    def _get_application_tables(self) -> List[str]:
        """Get list of application DynamoDB tables"""
        try:
            paginator = self.dynamodb.meta.client.get_paginator('list_tables')
            table_names = []
            
            for page in paginator.paginate():
                for table_name in page['TableNames']:
                    # Filter for application tables
                    if self.config.project_name in table_name and self.config.environment in table_name:
                        table_names.append(table_name)
                        
            return table_names
            
        except Exception as e:
            logger.error(f"Error listing DynamoDB tables: {str(e)}")
            return []

    def _backup_dynamodb_table(self, table_name: str) -> BackupResult:
        """Backup a single DynamoDB table"""
        start_time = datetime.utcnow()
        
        try:
            # Create on-demand backup
            response = self.backup_client.start_backup_job(
                BackupVaultName=self.config.backup_vault,
                ResourceArn=f"arn:aws:dynamodb:{self.config.aws_region}:*:table/{table_name}",
                IamRoleArn=self._get_backup_role_arn(),
                BackupOptions={
                    'WindowsVSS': 'disabled'
                },
                CompleteWindowMinutes=300,  # 5 hours
                StartWindowMinutes=60       # 1 hour
            )
            
            backup_job_id = response['BackupJobId']
            
            # Wait for backup completion (with timeout)
            self._wait_for_backup_completion(backup_job_id)
            
            # Get backup details
            backup_details = self.backup_client.describe_backup_job(BackupJobId=backup_job_id)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return BackupResult(
                success=True,
                backup_id=backup_job_id,
                size_bytes=backup_details.get('BackupSizeInBytes', 0),
                duration_seconds=duration,
                backup_type="dynamodb",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="dynamodb",
                timestamp=start_time
            )

    def backup_s3_buckets(self) -> List[BackupResult]:
        """Backup S3 buckets with cross-region replication"""
        logger.info("Starting S3 backup process")
        results = []
        
        try:
            # Get list of application S3 buckets
            buckets = self._get_application_buckets()
            
            for bucket_name in buckets:
                # Enable versioning if not already enabled
                self._ensure_bucket_versioning(bucket_name)
                
                # Setup cross-region replication
                if self.config.enable_cross_region:
                    result = self._setup_cross_region_replication(bucket_name)
                    results.append(result)
                
                # Create snapshot backup
                result = self._create_s3_snapshot(bucket_name)
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error during S3 backup: {str(e)}")
            results.append(BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=0,
                error_message=str(e),
                backup_type="s3"
            ))
            
        return results

    def _get_application_buckets(self) -> List[str]:
        """Get list of application S3 buckets"""
        try:
            response = self.s3_client.list_buckets()
            bucket_names = []
            
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                # Filter for application buckets
                if self.config.project_name in bucket_name and self.config.environment in bucket_name:
                    bucket_names.append(bucket_name)
                    
            return bucket_names
            
        except Exception as e:
            logger.error(f"Error listing S3 buckets: {str(e)}")
            return []

    def _ensure_bucket_versioning(self, bucket_name: str):
        """Ensure S3 bucket has versioning enabled"""
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            logger.info(f"Versioning enabled for bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Error enabling versioning for {bucket_name}: {str(e)}")

    def _setup_cross_region_replication(self, bucket_name: str) -> BackupResult:
        """Setup cross-region replication for S3 bucket"""
        start_time = datetime.utcnow()
        
        try:
            # Create destination bucket in DR region
            dr_bucket_name = f"{bucket_name}-dr"
            
            try:
                self.s3_client_dr.create_bucket(
                    Bucket=dr_bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.config.backup_region}
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'BucketAlreadyExists':
                    raise
            
            # Configure replication
            replication_config = {
                'Role': self._get_replication_role_arn(),
                'Rules': [
                    {
                        'ID': 'ReplicateEverything',
                        'Status': 'Enabled',
                        'Prefix': '',
                        'Destination': {
                            'Bucket': f'arn:aws:s3:::{dr_bucket_name}',
                            'StorageClass': 'STANDARD_IA'
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_replication(
                Bucket=bucket_name,
                ReplicationConfiguration=replication_config
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return BackupResult(
                success=True,
                backup_id=f"replication-{bucket_name}",
                size_bytes=0,  # Replication size calculated separately
                duration_seconds=duration,
                backup_type="s3_replication",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="s3_replication",
                timestamp=start_time
            )

    def _create_s3_snapshot(self, bucket_name: str) -> BackupResult:
        """Create a point-in-time snapshot of S3 bucket"""
        start_time = datetime.utcnow()
        
        try:
            # Create snapshot by copying to backup bucket with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            snapshot_prefix = f"snapshots/{timestamp}/"
            backup_bucket = f"{bucket_name}-snapshots"
            
            # Ensure backup bucket exists
            try:
                self.s3_client.create_bucket(Bucket=backup_bucket)
            except ClientError as e:
                if e.response['Error']['Code'] != 'BucketAlreadyExists':
                    raise
            
            # Copy all objects to snapshot
            paginator = self.s3_client.get_paginator('list_objects_v2')
            total_size = 0
            object_count = 0
            
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        source_key = obj['Key']
                        dest_key = f"{snapshot_prefix}{source_key}"
                        
                        copy_source = {'Bucket': bucket_name, 'Key': source_key}
                        self.s3_client.copy_object(
                            CopySource=copy_source,
                            Bucket=backup_bucket,
                            Key=dest_key
                        )
                        
                        total_size += obj['Size']
                        object_count += 1
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"S3 snapshot created: {object_count} objects, {total_size} bytes")
            
            return BackupResult(
                success=True,
                backup_id=f"snapshot-{bucket_name}-{timestamp}",
                size_bytes=total_size,
                duration_seconds=duration,
                backup_type="s3_snapshot",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="s3_snapshot",
                timestamp=start_time
            )

    def backup_configuration(self) -> List[BackupResult]:
        """Backup application configuration"""
        logger.info("Starting configuration backup process")
        results = []
        
        try:
            # Backup Parameter Store parameters
            param_result = self._backup_parameter_store()
            results.append(param_result)
            
            # Backup Secrets Manager secrets
            secrets_result = self._backup_secrets_manager()
            results.append(secrets_result)
            
            # Backup Lambda environment variables
            lambda_result = self._backup_lambda_configs()
            results.append(lambda_result)
            
        except Exception as e:
            logger.error(f"Error during configuration backup: {str(e)}")
            results.append(BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=0,
                error_message=str(e),
                backup_type="configuration"
            ))
            
        return results

    def _backup_parameter_store(self) -> BackupResult:
        """Backup AWS Parameter Store parameters"""
        start_time = datetime.utcnow()
        
        try:
            # Get all parameters for the application
            paginator = self.ssm_client.get_paginator('describe_parameters')
            parameters = []
            
            for page in paginator.paginate():
                for param in page['Parameters']:
                    if self.config.project_name in param['Name']:
                        # Get parameter value
                        response = self.ssm_client.get_parameter(
                            Name=param['Name'],
                            WithDecryption=True
                        )
                        parameters.append({
                            'Name': param['Name'],
                            'Value': response['Parameter']['Value'],
                            'Type': param['Type'],
                            'Description': param.get('Description', ''),
                            'LastModifiedDate': param.get('LastModifiedDate', '').isoformat() if param.get('LastModifiedDate') else ''
                        })
            
            # Save to S3
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'parameters': parameters
            }
            
            backup_key = f"configuration-backups/parameter-store/{datetime.utcnow().strftime('%Y/%m/%d')}/parameters.json"
            
            self.s3_client.put_object(
                Bucket=f"{self.config.project_name}-config-backup-{self.config.environment}",
                Key=backup_key,
                Body=json.dumps(backup_data, indent=2),
                ContentType='application/json',
                ServerSideEncryption='aws:kms'
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            backup_size = len(json.dumps(backup_data))
            
            return BackupResult(
                success=True,
                backup_id=backup_key,
                size_bytes=backup_size,
                duration_seconds=duration,
                backup_type="parameter_store",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="parameter_store",
                timestamp=start_time
            )

    def _backup_secrets_manager(self) -> BackupResult:
        """Backup AWS Secrets Manager secrets (metadata only)"""
        start_time = datetime.utcnow()
        
        try:
            secrets_client = self.session.client('secretsmanager', region_name=self.config.aws_region)
            
            # List all secrets for the application
            paginator = secrets_client.get_paginator('list_secrets')
            secrets_metadata = []
            
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    if self.config.project_name in secret['Name']:
                        secrets_metadata.append({
                            'Name': secret['Name'],
                            'ARN': secret['ARN'],
                            'Description': secret.get('Description', ''),
                            'KmsKeyId': secret.get('KmsKeyId', ''),
                            'RotationEnabled': secret.get('RotationEnabled', False),
                            'LastChangedDate': secret.get('LastChangedDate', '').isoformat() if secret.get('LastChangedDate') else '',
                            'Tags': secret.get('Tags', [])
                        })
            
            # Save metadata to S3 (not the actual secret values for security)
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'secrets_metadata': secrets_metadata,
                'note': 'This backup contains metadata only. Secret values are not included for security.'
            }
            
            backup_key = f"configuration-backups/secrets-manager/{datetime.utcnow().strftime('%Y/%m/%d')}/secrets-metadata.json"
            
            self.s3_client.put_object(
                Bucket=f"{self.config.project_name}-config-backup-{self.config.environment}",
                Key=backup_key,
                Body=json.dumps(backup_data, indent=2),
                ContentType='application/json',
                ServerSideEncryption='aws:kms'
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            backup_size = len(json.dumps(backup_data))
            
            return BackupResult(
                success=True,
                backup_id=backup_key,
                size_bytes=backup_size,
                duration_seconds=duration,
                backup_type="secrets_manager",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="secrets_manager",
                timestamp=start_time
            )

    def _backup_lambda_configs(self) -> BackupResult:
        """Backup Lambda function configurations"""
        start_time = datetime.utcnow()
        
        try:
            lambda_client = self.session.client('lambda', region_name=self.config.aws_region)
            
            # List all Lambda functions for the application
            paginator = lambda_client.get_paginator('list_functions')
            functions_config = []
            
            for page in paginator.paginate():
                for function in page['Functions']:
                    if self.config.project_name in function['FunctionName']:
                        # Get detailed function configuration
                        config_response = lambda_client.get_function_configuration(
                            FunctionName=function['FunctionName']
                        )
                        
                        # Remove sensitive data
                        config_response.pop('CodeSha256', None)
                        config_response.pop('CodeSize', None)
                        
                        functions_config.append(config_response)
            
            # Save to S3
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'lambda_configurations': functions_config
            }
            
            backup_key = f"configuration-backups/lambda/{datetime.utcnow().strftime('%Y/%m/%d')}/lambda-configs.json"
            
            self.s3_client.put_object(
                Bucket=f"{self.config.project_name}-config-backup-{self.config.environment}",
                Key=backup_key,
                Body=json.dumps(backup_data, indent=2, default=str),
                ContentType='application/json',
                ServerSideEncryption='aws:kms'
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            backup_size = len(json.dumps(backup_data, default=str))
            
            return BackupResult(
                success=True,
                backup_id=backup_key,
                size_bytes=backup_size,
                duration_seconds=duration,
                backup_type="lambda_config",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="lambda_config",
                timestamp=start_time
            )

    def backup_code_repository(self) -> BackupResult:
        """Backup code repository"""
        logger.info("Starting code repository backup process")
        start_time = datetime.utcnow()
        
        try:
            # Create a full Git bundle for backup
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            bundle_name = f"ai-nutritionist-repo-{timestamp}.bundle"
            
            # Create Git bundle
            subprocess.run([
                'git', 'bundle', 'create', bundle_name, '--all'
            ], check=True, cwd=os.getcwd())
            
            # Upload bundle to S3
            backup_bucket = f"{self.config.project_name}-repo-backup-{self.config.environment}"
            backup_key = f"repository-backups/{datetime.utcnow().strftime('%Y/%m/%d')}/{bundle_name}"
            
            with open(bundle_name, 'rb') as bundle_file:
                self.s3_client.put_object(
                    Bucket=backup_bucket,
                    Key=backup_key,
                    Body=bundle_file,
                    ServerSideEncryption='aws:kms'
                )
            
            # Get file size
            file_size = os.path.getsize(bundle_name)
            
            # Cleanup local bundle
            os.remove(bundle_name)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return BackupResult(
                success=True,
                backup_id=backup_key,
                size_bytes=file_size,
                duration_seconds=duration,
                backup_type="repository",
                timestamp=start_time
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return BackupResult(
                success=False,
                backup_id="",
                size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
                backup_type="repository",
                timestamp=start_time
            )

    def verify_backups(self, backup_results: List[BackupResult]) -> Dict[str, Any]:
        """Verify backup integrity and completeness"""
        logger.info("Starting backup verification process")
        
        verification_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_backups': len(backup_results),
            'successful_backups': 0,
            'failed_backups': 0,
            'verification_tests': [],
            'overall_status': 'UNKNOWN'
        }
        
        try:
            for result in backup_results:
                if result.success:
                    verification_results['successful_backups'] += 1
                    
                    # Perform verification based on backup type
                    if result.backup_type == 'dynamodb':
                        test_result = self._verify_dynamodb_backup(result.backup_id)
                    elif result.backup_type == 's3_snapshot':
                        test_result = self._verify_s3_backup(result.backup_id)
                    elif result.backup_type in ['parameter_store', 'secrets_manager', 'lambda_config']:
                        test_result = self._verify_config_backup(result.backup_id)
                    elif result.backup_type == 'repository':
                        test_result = self._verify_repository_backup(result.backup_id)
                    else:
                        test_result = {'status': 'SKIPPED', 'message': 'No verification available'}
                    
                    verification_results['verification_tests'].append({
                        'backup_id': result.backup_id,
                        'backup_type': result.backup_type,
                        'verification_status': test_result['status'],
                        'verification_message': test_result.get('message', ''),
                        'test_timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    verification_results['failed_backups'] += 1
            
            # Determine overall status
            if verification_results['failed_backups'] == 0:
                verification_results['overall_status'] = 'SUCCESS'
            elif verification_results['successful_backups'] > verification_results['failed_backups']:
                verification_results['overall_status'] = 'PARTIAL_SUCCESS'
            else:
                verification_results['overall_status'] = 'FAILURE'
                
        except Exception as e:
            logger.error(f"Error during backup verification: {str(e)}")
            verification_results['overall_status'] = 'ERROR'
            verification_results['error_message'] = str(e)
        
        return verification_results

    def _verify_dynamodb_backup(self, backup_job_id: str) -> Dict[str, str]:
        """Verify DynamoDB backup integrity"""
        try:
            # Check backup job status
            response = self.backup_client.describe_backup_job(BackupJobId=backup_job_id)
            
            if response['State'] == 'COMPLETED':
                return {'status': 'SUCCESS', 'message': 'Backup completed successfully'}
            else:
                return {'status': 'FAILURE', 'message': f"Backup in state: {response['State']}"}
                
        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

    def _verify_s3_backup(self, backup_id: str) -> Dict[str, str]:
        """Verify S3 backup integrity"""
        try:
            # Extract bucket and key from backup_id
            if backup_id.startswith('snapshot-'):
                # For snapshot backups, verify the snapshot exists
                parts = backup_id.split('-')
                if len(parts) >= 3:
                    bucket_name = f"{parts[1]}-snapshots"
                    timestamp = parts[2]
                    
                    # Check if snapshot objects exist
                    response = self.s3_client.list_objects_v2(
                        Bucket=bucket_name,
                        Prefix=f"snapshots/{timestamp}/"
                    )
                    
                    if 'Contents' in response and len(response['Contents']) > 0:
                        return {'status': 'SUCCESS', 'message': f"Snapshot contains {len(response['Contents'])} objects"}
                    else:
                        return {'status': 'FAILURE', 'message': 'Snapshot is empty or missing'}
            
            return {'status': 'SKIPPED', 'message': 'Unable to parse backup ID for verification'}
            
        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

    def _verify_config_backup(self, backup_key: str) -> Dict[str, str]:
        """Verify configuration backup integrity"""
        try:
            # Get the bucket name (assuming standard naming)
            bucket_name = f"{self.config.project_name}-config-backup-{self.config.environment}"
            
            # Check if backup object exists and get metadata
            response = self.s3_client.head_object(
                Bucket=bucket_name,
                Key=backup_key
            )
            
            content_length = response.get('ContentLength', 0)
            if content_length > 0:
                return {'status': 'SUCCESS', 'message': f"Config backup exists, size: {content_length} bytes"}
            else:
                return {'status': 'FAILURE', 'message': 'Config backup is empty'}
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {'status': 'FAILURE', 'message': 'Config backup not found'}
            else:
                return {'status': 'ERROR', 'message': str(e)}
        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

    def _verify_repository_backup(self, backup_key: str) -> Dict[str, str]:
        """Verify repository backup integrity"""
        try:
            # Get the bucket name
            bucket_name = f"{self.config.project_name}-repo-backup-{self.config.environment}"
            
            # Check if backup bundle exists
            response = self.s3_client.head_object(
                Bucket=bucket_name,
                Key=backup_key
            )
            
            content_length = response.get('ContentLength', 0)
            if content_length > 1024:  # Bundle should be at least 1KB
                return {'status': 'SUCCESS', 'message': f"Repository backup exists, size: {content_length} bytes"}
            else:
                return {'status': 'FAILURE', 'message': 'Repository backup is too small or empty'}
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {'status': 'FAILURE', 'message': 'Repository backup not found'}
            else:
                return {'status': 'ERROR', 'message': str(e)}
        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

    def send_notification(self, backup_results: List[BackupResult], verification_results: Dict[str, Any]):
        """Send backup notification via SNS"""
        try:
            # Prepare notification message
            successful_backups = sum(1 for r in backup_results if r.success)
            total_backups = len(backup_results)
            
            if verification_results['overall_status'] == 'SUCCESS':
                subject = f"✅ Backup Successful - {self.config.project_name} ({self.config.environment})"
                status_emoji = "✅"
            elif verification_results['overall_status'] == 'PARTIAL_SUCCESS':
                subject = f"⚠️ Backup Partial Success - {self.config.project_name} ({self.config.environment})"
                status_emoji = "⚠️"
            else:
                subject = f"❌ Backup Failed - {self.config.project_name} ({self.config.environment})"
                status_emoji = "❌"
            
            message = f"""
{status_emoji} AI Nutritionist Backup Report
Project: {self.config.project_name}
Environment: {self.config.environment}
Timestamp: {datetime.utcnow().isoformat()}

📊 Summary:
- Total Backups: {total_backups}
- Successful: {successful_backups}
- Failed: {total_backups - successful_backups}
- Overall Status: {verification_results['overall_status']}

🔍 Verification Results:
- Verified Backups: {len(verification_results['verification_tests'])}
- Verification Status: {verification_results['overall_status']}

📋 Backup Details:
"""
            
            for result in backup_results:
                status_icon = "✅" if result.success else "❌"
                size_mb = result.size_bytes / (1024 * 1024) if result.size_bytes > 0 else 0
                
                message += f"""
{status_icon} {result.backup_type.upper()}:
  - ID: {result.backup_id[:50]}{'...' if len(result.backup_id) > 50 else ''}
  - Size: {size_mb:.2f} MB
  - Duration: {result.duration_seconds:.2f}s
  - Status: {'SUCCESS' if result.success else 'FAILED'}
"""
                if not result.success and result.error_message:
                    message += f"  - Error: {result.error_message[:100]}{'...' if len(result.error_message) > 100 else ''}\n"
            
            message += f"""
🔗 Links:
- Backup Vault: {self.config.backup_vault}
- AWS Region: {self.config.aws_region}
- Backup Region: {self.config.backup_region}

📞 Support: devops@ainutritionist.com
"""
            
            # Send SNS notification
            self.sns_client.publish(
                TopicArn=f"arn:aws:sns:{self.config.aws_region}:*:{self.config.notification_sns_topic}",
                Subject=subject,
                Message=message
            )
            
            logger.info("Backup notification sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

    def publish_metrics(self, backup_results: List[BackupResult], verification_results: Dict[str, Any]):
        """Publish backup metrics to CloudWatch"""
        try:
            timestamp = datetime.utcnow()
            
            # Calculate metrics
            successful_backups = sum(1 for r in backup_results if r.success)
            total_backups = len(backup_results)
            success_rate = (successful_backups / total_backups * 100) if total_backups > 0 else 0
            
            total_size_gb = sum(r.size_bytes for r in backup_results if r.success) / (1024**3)
            avg_duration = sum(r.duration_seconds for r in backup_results if r.success) / successful_backups if successful_backups > 0 else 0
            
            # Publish metrics
            metrics = [
                {
                    'MetricName': 'BackupSuccessRate',
                    'Value': success_rate,
                    'Unit': 'Percent',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': self.config.environment},
                        {'Name': 'Project', 'Value': self.config.project_name}
                    ]
                },
                {
                    'MetricName': 'TotalBackupSizeGB',
                    'Value': total_size_gb,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': self.config.environment},
                        {'Name': 'Project', 'Value': self.config.project_name}
                    ]
                },
                {
                    'MetricName': 'AvgBackupDuration',
                    'Value': avg_duration,
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': self.config.environment},
                        {'Name': 'Project', 'Value': self.config.project_name}
                    ]
                },
                {
                    'MetricName': 'FailedBackups',
                    'Value': total_backups - successful_backups,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': self.config.environment},
                        {'Name': 'Project', 'Value': self.config.project_name}
                    ]
                }
            ]
            
            # Add metrics by backup type
            backup_types = set(r.backup_type for r in backup_results)
            for backup_type in backup_types:
                type_results = [r for r in backup_results if r.backup_type == backup_type]
                type_success_rate = sum(1 for r in type_results if r.success) / len(type_results) * 100
                
                metrics.append({
                    'MetricName': f'{backup_type.title()}BackupSuccessRate',
                    'Value': type_success_rate,
                    'Unit': 'Percent',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': self.config.environment},
                        {'Name': 'Project', 'Value': self.config.project_name},
                        {'Name': 'BackupType', 'Value': backup_type}
                    ]
                })
            
            # Publish all metrics
            for i in range(0, len(metrics), 20):  # CloudWatch limit is 20 metrics per call
                batch = metrics[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace='AI-Nutritionist/Backup',
                    MetricData=[{
                        'MetricName': m['MetricName'],
                        'Value': m['Value'],
                        'Unit': m['Unit'],
                        'Timestamp': timestamp,
                        'Dimensions': m['Dimensions']
                    } for m in batch]
                )
            
            logger.info("Backup metrics published to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish metrics: {str(e)}")

    def _wait_for_backup_completion(self, backup_job_id: str, timeout_minutes: int = 60):
        """Wait for backup job completion with timeout"""
        start_time = datetime.utcnow()
        timeout = timedelta(minutes=timeout_minutes)
        
        while datetime.utcnow() - start_time < timeout:
            try:
                response = self.backup_client.describe_backup_job(BackupJobId=backup_job_id)
                state = response['State']
                
                if state == 'COMPLETED':
                    return True
                elif state in ['FAILED', 'ABORTED', 'EXPIRED']:
                    raise Exception(f"Backup job failed with state: {state}")
                
                # Wait before checking again
                import time
                time.sleep(30)
                
            except Exception as e:
                if "does not exist" in str(e):
                    # Job might not be visible yet, continue waiting
                    import time
                    time.sleep(10)
                    continue
                else:
                    raise
        
        raise Exception(f"Backup job timeout after {timeout_minutes} minutes")

    def _get_backup_role_arn(self) -> str:
        """Get the IAM role ARN for AWS Backup"""
        return f"arn:aws:iam::*:role/{self.config.project_name}-backup-role-{self.config.environment}"

    def _get_replication_role_arn(self) -> str:
        """Get the IAM role ARN for S3 replication"""
        return f"arn:aws:iam::*:role/{self.config.project_name}-replication-role-{self.config.environment}"

    def run_full_backup(self) -> Dict[str, Any]:
        """Run complete backup process"""
        logger.info("Starting full backup process for AI Nutritionist")
        
        start_time = datetime.utcnow()
        all_results = []
        
        try:
            # 1. Backup DynamoDB tables
            logger.info("Phase 1: Backing up DynamoDB tables")
            dynamodb_results = self.backup_dynamodb_tables()
            all_results.extend(dynamodb_results)
            
            # 2. Backup S3 buckets
            logger.info("Phase 2: Backing up S3 buckets")
            s3_results = self.backup_s3_buckets()
            all_results.extend(s3_results)
            
            # 3. Backup configuration
            logger.info("Phase 3: Backing up configuration")
            config_results = self.backup_configuration()
            all_results.extend(config_results)
            
            # 4. Backup code repository
            logger.info("Phase 4: Backing up code repository")
            repo_result = self.backup_code_repository()
            all_results.append(repo_result)
            
            # 5. Verify backups
            logger.info("Phase 5: Verifying backups")
            verification_results = self.verify_backups(all_results)
            
            # 6. Send notifications
            logger.info("Phase 6: Sending notifications")
            self.send_notification(all_results, verification_results)
            
            # 7. Publish metrics
            logger.info("Phase 7: Publishing metrics")
            self.publish_metrics(all_results, verification_results)
            
            total_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Prepare final report
            report = {
                'timestamp': start_time.isoformat(),
                'duration_seconds': total_duration,
                'backup_results': [asdict(r) for r in all_results],
                'verification_results': verification_results,
                'summary': {
                    'total_backups': len(all_results),
                    'successful_backups': sum(1 for r in all_results if r.success),
                    'failed_backups': sum(1 for r in all_results if not r.success),
                    'total_size_mb': sum(r.size_bytes for r in all_results if r.success) / (1024*1024),
                    'overall_status': verification_results['overall_status']
                }
            }
            
            logger.info(f"Full backup completed in {total_duration:.2f} seconds")
            logger.info(f"Overall status: {verification_results['overall_status']}")
            
            return report
            
        except Exception as e:
            logger.error(f"Full backup process failed: {str(e)}")
            total_duration = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'timestamp': start_time.isoformat(),
                'duration_seconds': total_duration,
                'backup_results': [asdict(r) for r in all_results],
                'error': str(e),
                'summary': {
                    'total_backups': len(all_results),
                    'successful_backups': sum(1 for r in all_results if r.success),
                    'failed_backups': sum(1 for r in all_results if not r.success),
                    'overall_status': 'FAILED'
                }
            }


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='AI Nutritionist Backup Automation')
    parser.add_argument('--environment', '-e', default='prod', help='Environment (dev/staging/prod)')
    parser.add_argument('--project-name', '-p', default='ai-nutritionist', help='Project name')
    parser.add_argument('--aws-region', '-r', default='us-east-1', help='AWS region')
    parser.add_argument('--backup-region', '-br', default='us-west-2', help='Backup region')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without making changes')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing backups')
    parser.add_argument('--backup-type', choices=['all', 'dynamodb', 's3', 'config', 'repository'], 
                       default='all', help='Type of backup to perform')
    
    args = parser.parse_args()
    
    # Create configuration
    config = BackupConfig(
        project_name=args.project_name,
        environment=args.environment,
        aws_region=args.aws_region,
        backup_region=args.backup_region
    )
    
    # Create backup automation instance
    backup_automation = BackupAutomation(config)
    
    if args.verify_only:
        # TODO: Implement verification-only mode
        logger.info("Verification-only mode not yet implemented")
        return
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No actual backups will be performed")
        return
    
    # Run backup based on type
    if args.backup_type == 'all':
        result = backup_automation.run_full_backup()
    elif args.backup_type == 'dynamodb':
        results = backup_automation.backup_dynamodb_tables()
        verification = backup_automation.verify_backups(results)
        result = {'backup_results': results, 'verification_results': verification}
    elif args.backup_type == 's3':
        results = backup_automation.backup_s3_buckets()
        verification = backup_automation.verify_backups(results)
        result = {'backup_results': results, 'verification_results': verification}
    elif args.backup_type == 'config':
        results = backup_automation.backup_configuration()
        verification = backup_automation.verify_backups(results)
        result = {'backup_results': results, 'verification_results': verification}
    elif args.backup_type == 'repository':
        repo_result = backup_automation.backup_code_repository()
        verification = backup_automation.verify_backups([repo_result])
        result = {'backup_results': [repo_result], 'verification_results': verification}
    
    # Print summary
    print("\n" + "="*80)
    print("BACKUP SUMMARY")
    print("="*80)
    print(f"Overall Status: {result.get('summary', {}).get('overall_status', 'UNKNOWN')}")
    print(f"Total Backups: {result.get('summary', {}).get('total_backups', 0)}")
    print(f"Successful: {result.get('summary', {}).get('successful_backups', 0)}")
    print(f"Failed: {result.get('summary', {}).get('failed_backups', 0)}")
    print(f"Total Size: {result.get('summary', {}).get('total_size_mb', 0):.2f} MB")
    
    if result.get('summary', {}).get('overall_status') in ['FAILED', 'PARTIAL_SUCCESS']:
        sys.exit(1)


if __name__ == "__main__":
    main()
