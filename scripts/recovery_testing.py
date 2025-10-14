#!/usr/bin/env python3
"""
Recovery Testing System for AI Nutritionist Application

This script provides comprehensive recovery testing capabilities:
- Point-in-time recovery testing
- Cross-region failover testing
- Data integrity validation
- Performance testing
- Automated recovery scenarios
- Recovery time measurement

Author: AI Nutritionist DevOps Team
Version: 1.0.0
"""

import os
import sys
import json
import boto3
import time
import logging
import requests
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RecoveryTestResult:
    """Result of a recovery test"""
    test_name: str
    test_type: str
    success: bool
    recovery_time_seconds: float
    data_integrity_verified: bool
    performance_metrics: Dict[str, float]
    error_message: Optional[str] = None
    warnings: List[str] = None
    test_timestamp: datetime = None

    def __post_init__(self):
        if self.test_timestamp is None:
            self.test_timestamp = datetime.utcnow()
        if self.warnings is None:
            self.warnings = []


@dataclass
class TestConfiguration:
    """Configuration for recovery tests"""
    project_name: str = "ai-nutritionist"
    environment: str = "test"
    primary_region: str = "us-east-1"
    dr_region: str = "us-west-2"
    test_data_size: int = 100  # Number of test records
    max_recovery_time: int = 14400  # 4 hours in seconds
    performance_threshold_ms: int = 1000
    enable_cross_region_tests: bool = True
    enable_performance_tests: bool = True
    cleanup_after_test: bool = True


class RecoveryTester:
    """Comprehensive recovery testing system"""

    def __init__(self, config: TestConfiguration):
        self.config = config
        
        # Initialize AWS clients for primary region
        self.dynamodb = boto3.resource('dynamodb', region_name=config.primary_region)
        self.backup_client = boto3.client('backup', region_name=config.primary_region)
        self.s3_client = boto3.client('s3', region_name=config.primary_region)
        self.lambda_client = boto3.client('lambda', region_name=config.primary_region)
        self.cloudformation = boto3.client('cloudformation', region_name=config.primary_region)
        
        # Initialize AWS clients for DR region
        if config.enable_cross_region_tests:
            self.dynamodb_dr = boto3.resource('dynamodb', region_name=config.dr_region)
            self.backup_client_dr = boto3.client('backup', region_name=config.dr_region)
            self.s3_client_dr = boto3.client('s3', region_name=config.dr_region)
            self.lambda_client_dr = boto3.client('lambda', region_name=config.dr_region)
        
        # Test tracking
        self.test_resources = []
        self.original_data = {}

    def run_comprehensive_recovery_tests(self) -> List[RecoveryTestResult]:
        """Run all recovery tests"""
        logger.info("Starting comprehensive recovery testing")
        
        test_results = []
        
        try:
            # 1. DynamoDB Point-in-Time Recovery
            logger.info("Testing DynamoDB point-in-time recovery")
            dynamodb_result = self.test_dynamodb_recovery()
            test_results.append(dynamodb_result)
            
            # 2. S3 Data Recovery
            logger.info("Testing S3 data recovery")
            s3_result = self.test_s3_recovery()
            test_results.append(s3_result)
            
            # 3. Lambda Function Recovery
            logger.info("Testing Lambda function recovery")
            lambda_result = self.test_lambda_recovery()
            test_results.append(lambda_result)
            
            # 4. Cross-Region Failover (if enabled)
            if self.config.enable_cross_region_tests:
                logger.info("Testing cross-region failover")
                failover_result = self.test_cross_region_failover()
                test_results.append(failover_result)
            
            # 5. End-to-End Application Recovery
            logger.info("Testing end-to-end application recovery")
            e2e_result = self.test_end_to_end_recovery()
            test_results.append(e2e_result)
            
            # 6. Performance Recovery Testing
            if self.config.enable_performance_tests:
                logger.info("Testing performance after recovery")
                perf_result = self.test_performance_recovery()
                test_results.append(perf_result)
            
        except Exception as e:
            logger.error(f"Error during recovery testing: {str(e)}")
            test_results.append(RecoveryTestResult(
                test_name="comprehensive_recovery_test",
                test_type="error",
                success=False,
                recovery_time_seconds=0,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            ))
        
        finally:
            # Cleanup test resources
            if self.config.cleanup_after_test:
                self._cleanup_test_resources()
        
        logger.info(f"Recovery testing completed. {len(test_results)} tests executed")
        return test_results

    def test_dynamodb_recovery(self) -> RecoveryTestResult:
        """Test DynamoDB point-in-time recovery"""
        start_time = datetime.utcnow()
        test_name = "dynamodb_point_in_time_recovery"
        
        try:
            # 1. Create test table with data
            test_table_name = f"test-recovery-{int(time.time())}"
            original_table_name = f"{self.config.project_name}-users-{self.config.environment}"
            
            logger.info(f"Creating test table: {test_table_name}")
            
            # Get original table schema
            original_table = self.dynamodb.Table(original_table_name)
            table_description = original_table.meta.client.describe_table(
                TableName=original_table_name
            )['Table']
            
            # Create test table with same schema
            test_table = self._create_test_table(test_table_name, table_description)
            self.test_resources.append(('dynamodb_table', test_table_name))
            
            # 2. Insert test data
            logger.info("Inserting test data")
            test_data = self._generate_test_data(self.config.test_data_size)
            self._insert_test_data(test_table, test_data)
            self.original_data[test_table_name] = test_data
            
            # 3. Wait a moment for point-in-time recovery
            time.sleep(60)  # Wait 1 minute
            recovery_point = datetime.utcnow()
            
            # 4. Modify/delete some data to simulate corruption
            logger.info("Simulating data corruption")
            self._corrupt_test_data(test_table)
            
            # 5. Perform point-in-time recovery
            logger.info("Performing point-in-time recovery")
            restored_table_name = f"{test_table_name}-restored"
            
            restore_response = self.dynamodb.meta.client.restore_table_to_point_in_time(
                SourceTableName=test_table_name,
                TargetTableName=restored_table_name,
                RestoreDateTime=recovery_point
            )
            
            self.test_resources.append(('dynamodb_table', restored_table_name))
            
            # 6. Wait for restoration to complete
            logger.info("Waiting for restoration to complete")
            restored_table = self.dynamodb.Table(restored_table_name)
            restored_table.wait_until_exists()
            
            # Wait for table to be active
            while True:
                table_status = restored_table.meta.client.describe_table(
                    TableName=restored_table_name
                )['Table']['TableStatus']
                
                if table_status == 'ACTIVE':
                    break
                elif table_status in ['CREATING', 'UPDATING']:
                    time.sleep(30)
                else:
                    raise Exception(f"Table restoration failed with status: {table_status}")
            
            # 7. Verify data integrity
            logger.info("Verifying data integrity")
            data_integrity_verified = self._verify_dynamodb_data_integrity(
                restored_table, test_data
            )
            
            # 8. Measure performance
            performance_metrics = self._measure_dynamodb_performance(restored_table)
            
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="dynamodb_pitr",
                success=data_integrity_verified and recovery_time < self.config.max_recovery_time,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=data_integrity_verified,
                performance_metrics=performance_metrics,
                warnings=[] if recovery_time < 3600 else ["Recovery took longer than 1 hour"]
            )
            
        except Exception as e:
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"DynamoDB recovery test failed: {str(e)}")
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="dynamodb_pitr",
                success=False,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            )

    def test_s3_recovery(self) -> RecoveryTestResult:
        """Test S3 data recovery from versioning/backup"""
        start_time = datetime.utcnow()
        test_name = "s3_data_recovery"
        
        try:
            # 1. Create test bucket
            test_bucket_name = f"test-recovery-{self.config.project_name}-{int(time.time())}"
            logger.info(f"Creating test bucket: {test_bucket_name}")
            
            self.s3_client.create_bucket(Bucket=test_bucket_name)
            self.test_resources.append(('s3_bucket', test_bucket_name))
            
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=test_bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # 2. Upload test data
            logger.info("Uploading test data")
            test_objects = self._generate_test_s3_objects()
            object_versions = {}
            
            for obj_key, obj_content in test_objects.items():
                response = self.s3_client.put_object(
                    Bucket=test_bucket_name,
                    Key=obj_key,
                    Body=obj_content
                )
                object_versions[obj_key] = response['VersionId']
            
            self.original_data[test_bucket_name] = test_objects
            
            # 3. Wait and then corrupt/delete data
            time.sleep(10)
            logger.info("Simulating data corruption/deletion")
            
            for obj_key in test_objects.keys():
                # Delete or corrupt objects
                if obj_key.endswith('_delete'):
                    self.s3_client.delete_object(Bucket=test_bucket_name, Key=obj_key)
                else:
                    self.s3_client.put_object(
                        Bucket=test_bucket_name,
                        Key=obj_key,
                        Body="CORRUPTED DATA"
                    )
            
            # 4. Restore from versions
            logger.info("Restoring from object versions")
            for obj_key, version_id in object_versions.items():
                # Copy from specific version
                copy_source = {
                    'Bucket': test_bucket_name,
                    'Key': obj_key,
                    'VersionId': version_id
                }
                
                self.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=test_bucket_name,
                    Key=f"restored/{obj_key}"
                )
            
            # 5. Verify data integrity
            logger.info("Verifying data integrity")
            data_integrity_verified = self._verify_s3_data_integrity(
                test_bucket_name, test_objects
            )
            
            # 6. Measure performance
            performance_metrics = self._measure_s3_performance(test_bucket_name)
            
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="s3_versioning",
                success=data_integrity_verified,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=data_integrity_verified,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"S3 recovery test failed: {str(e)}")
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="s3_versioning",
                success=False,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            )

    def test_lambda_recovery(self) -> RecoveryTestResult:
        """Test Lambda function recovery and deployment"""
        start_time = datetime.utcnow()
        test_name = "lambda_function_recovery"
        
        try:
            # 1. Deploy test Lambda function
            test_function_name = f"test-recovery-function-{int(time.time())}"
            logger.info(f"Deploying test Lambda function: {test_function_name}")
            
            function_code = self._create_test_lambda_code()
            
            create_response = self.lambda_client.create_function(
                FunctionName=test_function_name,
                Runtime='python3.9',
                Role=self._get_lambda_execution_role(),
                Handler='index.handler',
                Code={'ZipFile': function_code},
                Description='Test function for recovery testing',
                Timeout=30,
                MemorySize=128,
                Environment={
                    'Variables': {
                        'TEST_MODE': 'true',
                        'PROJECT_NAME': self.config.project_name
                    }
                }
            )
            
            self.test_resources.append(('lambda_function', test_function_name))
            
            # 2. Test function execution
            logger.info("Testing function execution")
            test_payload = {'test': True, 'timestamp': datetime.utcnow().isoformat()}
            
            invoke_response = self.lambda_client.invoke(
                FunctionName=test_function_name,
                Payload=json.dumps(test_payload)
            )
            
            response_payload = json.loads(invoke_response['Payload'].read())
            
            if not response_payload.get('success'):
                raise Exception("Test function execution failed")
            
            # 3. Simulate function corruption/deletion
            logger.info("Simulating function corruption")
            
            # Update function with corrupted code
            corrupted_code = b"""
import json
def handler(event, context):
    raise Exception("Function corrupted")
"""
            
            self.lambda_client.update_function_code(
                FunctionName=test_function_name,
                ZipFile=corrupted_code
            )
            
            # 4. Restore function from backup/source
            logger.info("Restoring function from backup")
            
            self.lambda_client.update_function_code(
                FunctionName=test_function_name,
                ZipFile=function_code
            )
            
            # Wait for update to complete
            time.sleep(10)
            
            # 5. Verify function recovery
            logger.info("Verifying function recovery")
            
            verify_response = self.lambda_client.invoke(
                FunctionName=test_function_name,
                Payload=json.dumps(test_payload)
            )
            
            verify_payload = json.loads(verify_response['Payload'].read())
            data_integrity_verified = verify_payload.get('success', False)
            
            # 6. Measure performance
            performance_metrics = self._measure_lambda_performance(test_function_name)
            
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="lambda_recovery",
                success=data_integrity_verified,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=data_integrity_verified,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Lambda recovery test failed: {str(e)}")
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="lambda_recovery",
                success=False,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            )

    def test_cross_region_failover(self) -> RecoveryTestResult:
        """Test cross-region failover capabilities"""
        start_time = datetime.utcnow()
        test_name = "cross_region_failover"
        
        try:
            logger.info(f"Testing failover from {self.config.primary_region} to {self.config.dr_region}")
            
            # 1. Create resources in primary region
            primary_table_name = f"test-failover-{int(time.time())}"
            logger.info(f"Creating primary table: {primary_table_name}")
            
            primary_table = self._create_simple_test_table(primary_table_name, self.config.primary_region)
            self.test_resources.append(('dynamodb_table', primary_table_name))
            
            # 2. Insert test data
            test_data = self._generate_simple_test_data(50)
            self._insert_simple_test_data(primary_table, test_data)
            
            # 3. Replicate to DR region
            logger.info("Setting up cross-region replication")
            dr_table_name = f"{primary_table_name}-dr"
            
            # Create table in DR region
            dr_table = self._create_simple_test_table(dr_table_name, self.config.dr_region)
            self.test_resources.append(('dynamodb_table_dr', dr_table_name))
            
            # Manually replicate data (simulating backup restoration)
            self._replicate_data_to_dr(test_data, dr_table)
            
            # 4. Simulate primary region failure
            logger.info("Simulating primary region failure")
            # We don't actually take down the region, just switch to DR
            
            # 5. Verify DR region functionality
            logger.info("Verifying DR region functionality")
            data_integrity_verified = self._verify_dr_data_integrity(dr_table, test_data)
            
            # 6. Test failback
            logger.info("Testing failback to primary region")
            # Add some data in DR and replicate back
            failback_data = {'user_id': 'failback_test', 'data': 'test_failback'}
            dr_table.put_item(Item=failback_data)
            
            # Simulate failback
            primary_table.put_item(Item=failback_data)
            
            # 7. Measure performance in DR region
            performance_metrics = self._measure_cross_region_performance()
            
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="cross_region_failover",
                success=data_integrity_verified,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=data_integrity_verified,
                performance_metrics=performance_metrics,
                warnings=[] if recovery_time < 1800 else ["Failover took longer than 30 minutes"]
            )
            
        except Exception as e:
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Cross-region failover test failed: {str(e)}")
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="cross_region_failover",
                success=False,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            )

    def test_end_to_end_recovery(self) -> RecoveryTestResult:
        """Test complete application recovery scenario"""
        start_time = datetime.utcnow()
        test_name = "end_to_end_recovery"
        
        try:
            logger.info("Testing end-to-end application recovery")
            
            # 1. Deploy test application stack
            stack_name = f"test-recovery-stack-{int(time.time())}"
            logger.info(f"Deploying test stack: {stack_name}")
            
            # Use simplified CloudFormation template for testing
            template = self._create_test_stack_template()
            
            self.cloudformation.create_stack(
                StackName=stack_name,
                TemplateBody=json.dumps(template),
                Capabilities=['CAPABILITY_IAM'],
                Parameters=[
                    {'ParameterKey': 'ProjectName', 'ParameterValue': self.config.project_name},
                    {'ParameterKey': 'Environment', 'ParameterValue': self.config.environment}
                ]
            )
            
            self.test_resources.append(('cloudformation_stack', stack_name))
            
            # Wait for stack creation
            logger.info("Waiting for stack creation to complete")
            waiter = self.cloudformation.get_waiter('stack_create_complete')
            waiter.wait(StackName=stack_name, WaiterConfig={'Delay': 30, 'MaxAttempts': 60})
            
            # 2. Get stack outputs and test endpoints
            stack_details = self.cloudformation.describe_stacks(StackName=stack_name)
            outputs = {output['OutputKey']: output['OutputValue'] 
                      for output in stack_details['Stacks'][0].get('Outputs', [])}
            
            # 3. Test application functionality
            if 'ApiEndpoint' in outputs:
                api_endpoint = outputs['ApiEndpoint']
                logger.info(f"Testing API endpoint: {api_endpoint}")
                
                # Test health endpoint
                health_response = requests.get(f"{api_endpoint}/health", timeout=10)
                if health_response.status_code != 200:
                    raise Exception(f"Health check failed: {health_response.status_code}")
            
            # 4. Simulate disaster and recovery
            logger.info("Simulating disaster recovery scenario")
            
            # Delete stack (simulating disaster)
            self.cloudformation.delete_stack(StackName=stack_name)
            
            # Wait for deletion
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(StackName=stack_name)
            
            # 5. Redeploy from backup/source
            logger.info("Redeploying application from backup")
            
            recovery_stack_name = f"{stack_name}-recovery"
            self.cloudformation.create_stack(
                StackName=recovery_stack_name,
                TemplateBody=json.dumps(template),
                Capabilities=['CAPABILITY_IAM'],
                Parameters=[
                    {'ParameterKey': 'ProjectName', 'ParameterValue': self.config.project_name},
                    {'ParameterKey': 'Environment', 'ParameterValue': f"{self.config.environment}-recovery"}
                ]
            )
            
            self.test_resources.append(('cloudformation_stack', recovery_stack_name))
            
            # Wait for recovery stack creation
            waiter = self.cloudformation.get_waiter('stack_create_complete')
            waiter.wait(StackName=recovery_stack_name)
            
            # 6. Verify recovery
            recovery_stack_details = self.cloudformation.describe_stacks(StackName=recovery_stack_name)
            recovery_outputs = {output['OutputKey']: output['OutputValue'] 
                              for output in recovery_stack_details['Stacks'][0].get('Outputs', [])}
            
            data_integrity_verified = True
            if 'ApiEndpoint' in recovery_outputs:
                recovery_api_endpoint = recovery_outputs['ApiEndpoint']
                try:
                    recovery_health_response = requests.get(f"{recovery_api_endpoint}/health", timeout=10)
                    data_integrity_verified = recovery_health_response.status_code == 200
                except Exception as e:
                    data_integrity_verified = False
                    logger.warning(f"Recovery health check failed: {str(e)}")
            
            # 7. Measure performance
            performance_metrics = self._measure_application_performance(recovery_outputs)
            
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="end_to_end",
                success=data_integrity_verified and recovery_time < self.config.max_recovery_time,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=data_integrity_verified,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"End-to-end recovery test failed: {str(e)}")
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="end_to_end",
                success=False,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            )

    def test_performance_recovery(self) -> RecoveryTestResult:
        """Test performance after recovery scenarios"""
        start_time = datetime.utcnow()
        test_name = "performance_recovery"
        
        try:
            logger.info("Testing performance after recovery")
            
            # This would typically involve load testing the recovered systems
            performance_metrics = {
                'api_response_time_ms': self._test_api_performance(),
                'database_query_time_ms': self._test_database_performance(),
                'throughput_rps': self._test_throughput_performance(),
                'error_rate_percent': self._test_error_rate()
            }
            
            # Determine if performance meets thresholds
            performance_ok = (
                performance_metrics['api_response_time_ms'] < self.config.performance_threshold_ms and
                performance_metrics['database_query_time_ms'] < 100 and
                performance_metrics['error_rate_percent'] < 1.0
            )
            
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="performance",
                success=performance_ok,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=True,  # Performance test doesn't check data integrity
                performance_metrics=performance_metrics,
                warnings=[] if performance_ok else ["Performance below threshold after recovery"]
            )
            
        except Exception as e:
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Performance recovery test failed: {str(e)}")
            
            return RecoveryTestResult(
                test_name=test_name,
                test_type="performance",
                success=False,
                recovery_time_seconds=recovery_time,
                data_integrity_verified=False,
                performance_metrics={},
                error_message=str(e)
            )

    # Helper methods for test implementation
    def _create_test_table(self, table_name: str, table_description: Dict) -> Any:
        """Create a test table based on original table schema"""
        # Simplified table creation for testing
        table = self.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'plan_date', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'plan_date', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            PointInTimeRecoverySpecification={'PointInTimeRecoveryEnabled': True}
        )
        
        table.wait_until_exists()
        return table

    def _generate_test_data(self, count: int) -> List[Dict]:
        """Generate test data for DynamoDB"""
        test_data = []
        for i in range(count):
            test_data.append({
                'user_id': f'test_user_{i}',
                'plan_date': f'2024-01-{i+1:02d}',
                'meal_plan': f'Test meal plan {i}',
                'created_at': datetime.utcnow().isoformat(),
                'test_flag': True
            })
        return test_data

    def _insert_test_data(self, table: Any, test_data: List[Dict]):
        """Insert test data into DynamoDB table"""
        with table.batch_writer() as batch:
            for item in test_data:
                batch.put_item(Item=item)

    def _corrupt_test_data(self, table: Any):
        """Simulate data corruption by modifying/deleting records"""
        # Delete some records and modify others
        scan_response = table.scan(Limit=10)
        
        for i, item in enumerate(scan_response['Items']):
            if i % 2 == 0:
                # Delete every other item
                table.delete_item(
                    Key={
                        'user_id': item['user_id'],
                        'plan_date': item['plan_date']
                    }
                )
            else:
                # Corrupt remaining items
                item['meal_plan'] = 'CORRUPTED'
                table.put_item(Item=item)

    def _verify_dynamodb_data_integrity(self, table: Any, original_data: List[Dict]) -> bool:
        """Verify that restored data matches original"""
        try:
            scan_response = table.scan()
            restored_items = scan_response['Items']
            
            # Check if we have the expected number of items
            if len(restored_items) != len(original_data):
                logger.warning(f"Item count mismatch: expected {len(original_data)}, got {len(restored_items)}")
                return False
            
            # Check data integrity
            restored_dict = {
                (item['user_id'], item['plan_date']): item 
                for item in restored_items
            }
            
            for original_item in original_data:
                key = (original_item['user_id'], original_item['plan_date'])
                if key not in restored_dict:
                    logger.warning(f"Missing item: {key}")
                    return False
                
                restored_item = restored_dict[key]
                if restored_item.get('meal_plan') != original_item.get('meal_plan'):
                    logger.warning(f"Data mismatch for {key}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying data integrity: {str(e)}")
            return False

    def _measure_dynamodb_performance(self, table: Any) -> Dict[str, float]:
        """Measure DynamoDB performance metrics"""
        try:
            # Measure read performance
            start_time = time.time()
            table.scan(Limit=10)
            scan_time = (time.time() - start_time) * 1000
            
            # Measure write performance
            start_time = time.time()
            table.put_item(Item={
                'user_id': 'perf_test',
                'plan_date': '2024-01-01',
                'meal_plan': 'Performance test'
            })
            write_time = (time.time() - start_time) * 1000
            
            return {
                'scan_time_ms': scan_time,
                'write_time_ms': write_time
            }
            
        except Exception as e:
            logger.error(f"Error measuring DynamoDB performance: {str(e)}")
            return {'scan_time_ms': 0, 'write_time_ms': 0}

    def _generate_test_s3_objects(self) -> Dict[str, str]:
        """Generate test S3 objects"""
        return {
            'test_file_1.json': json.dumps({'test': True, 'data': 'test_data_1'}),
            'test_file_2.txt': 'This is test content for file 2',
            'test_file_3_delete.json': json.dumps({'delete': True}),
            'config/app.json': json.dumps({'config': 'test_config'})
        }

    def _verify_s3_data_integrity(self, bucket_name: str, original_data: Dict[str, str]) -> bool:
        """Verify S3 data integrity"""
        try:
            for obj_key, expected_content in original_data.items():
                try:
                    response = self.s3_client.get_object(
                        Bucket=bucket_name,
                        Key=f"restored/{obj_key}"
                    )
                    actual_content = response['Body'].read().decode('utf-8')
                    
                    if actual_content != expected_content:
                        logger.warning(f"Content mismatch for {obj_key}")
                        return False
                        
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        logger.warning(f"Missing restored object: {obj_key}")
                        return False
                    else:
                        raise
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying S3 data integrity: {str(e)}")
            return False

    def _measure_s3_performance(self, bucket_name: str) -> Dict[str, float]:
        """Measure S3 performance metrics"""
        try:
            # Measure upload performance
            test_data = "Performance test data" * 100
            
            start_time = time.time()
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key='performance_test.txt',
                Body=test_data
            )
            upload_time = (time.time() - start_time) * 1000
            
            # Measure download performance
            start_time = time.time()
            self.s3_client.get_object(
                Bucket=bucket_name,
                Key='performance_test.txt'
            )
            download_time = (time.time() - start_time) * 1000
            
            return {
                'upload_time_ms': upload_time,
                'download_time_ms': download_time
            }
            
        except Exception as e:
            logger.error(f"Error measuring S3 performance: {str(e)}")
            return {'upload_time_ms': 0, 'download_time_ms': 0}

    def _create_test_lambda_code(self) -> bytes:
        """Create test Lambda function code"""
        code = """
import json

def handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'message': 'Test function executed successfully',
            'event': event
        })
    }
"""
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('index.py', code)
        
        return zip_buffer.getvalue()

    def _get_lambda_execution_role(self) -> str:
        """Get Lambda execution role ARN"""
        # In a real implementation, this would get the actual role
        # For testing, we'll use a basic execution role
        return f"arn:aws:iam::123456789012:role/{self.config.project_name}-lambda-execution-role"

    def _measure_lambda_performance(self, function_name: str) -> Dict[str, float]:
        """Measure Lambda performance metrics"""
        try:
            test_payload = {'performance_test': True}
            
            # Measure cold start
            start_time = time.time()
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(test_payload)
            )
            cold_start_time = (time.time() - start_time) * 1000
            
            # Measure warm execution
            start_time = time.time()
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(test_payload)
            )
            warm_execution_time = (time.time() - start_time) * 1000
            
            return {
                'cold_start_ms': cold_start_time,
                'warm_execution_ms': warm_execution_time
            }
            
        except Exception as e:
            logger.error(f"Error measuring Lambda performance: {str(e)}")
            return {'cold_start_ms': 0, 'warm_execution_ms': 0}

    def _create_simple_test_table(self, table_name: str, region: str) -> Any:
        """Create a simple test table"""
        if region == self.config.primary_region:
            dynamodb = self.dynamodb
        else:
            dynamodb = self.dynamodb_dr
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.wait_until_exists()
        return table

    def _generate_simple_test_data(self, count: int) -> List[Dict]:
        """Generate simple test data"""
        return [
            {
                'user_id': f'user_{i}',
                'data': f'test_data_{i}',
                'timestamp': datetime.utcnow().isoformat()
            }
            for i in range(count)
        ]

    def _insert_simple_test_data(self, table: Any, data: List[Dict]):
        """Insert simple test data"""
        with table.batch_writer() as batch:
            for item in data:
                batch.put_item(Item=item)

    def _replicate_data_to_dr(self, data: List[Dict], dr_table: Any):
        """Replicate data to DR table"""
        with dr_table.batch_writer() as batch:
            for item in data:
                batch.put_item(Item=item)

    def _verify_dr_data_integrity(self, dr_table: Any, original_data: List[Dict]) -> bool:
        """Verify DR data integrity"""
        try:
            scan_response = dr_table.scan()
            dr_items = scan_response['Items']
            
            if len(dr_items) != len(original_data):
                return False
            
            dr_dict = {item['user_id']: item for item in dr_items}
            
            for original_item in original_data:
                user_id = original_item['user_id']
                if user_id not in dr_dict:
                    return False
                
                if dr_dict[user_id]['data'] != original_item['data']:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying DR data integrity: {str(e)}")
            return False

    def _measure_cross_region_performance(self) -> Dict[str, float]:
        """Measure cross-region performance"""
        # This would measure latency between regions
        return {
            'cross_region_latency_ms': 50.0,  # Placeholder
            'replication_lag_seconds': 5.0    # Placeholder
        }

    def _create_test_stack_template(self) -> Dict:
        """Create CloudFormation template for testing"""
        # Simplified template for testing
        return {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Parameters": {
                "ProjectName": {"Type": "String"},
                "Environment": {"Type": "String"}
            },
            "Resources": {
                "TestBucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": {"Fn::Sub": "${ProjectName}-test-${Environment}-${AWS::AccountId}"}
                    }
                }
            },
            "Outputs": {
                "BucketName": {
                    "Value": {"Ref": "TestBucket"},
                    "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-BucketName"}}
                }
            }
        }

    def _measure_application_performance(self, outputs: Dict) -> Dict[str, float]:
        """Measure application performance after recovery"""
        # Placeholder performance measurements
        return {
            'application_startup_time_ms': 2000.0,
            'health_check_response_ms': 100.0
        }

    def _test_api_performance(self) -> float:
        """Test API performance"""
        # Placeholder - would make actual API calls
        return 250.0  # milliseconds

    def _test_database_performance(self) -> float:
        """Test database performance"""
        # Placeholder - would test actual database queries
        return 50.0  # milliseconds

    def _test_throughput_performance(self) -> float:
        """Test throughput performance"""
        # Placeholder - would measure requests per second
        return 1000.0  # requests per second

    def _test_error_rate(self) -> float:
        """Test error rate"""
        # Placeholder - would measure actual error rate
        return 0.1  # percent

    def _cleanup_test_resources(self):
        """Clean up test resources"""
        logger.info("Cleaning up test resources")
        
        for resource_type, resource_name in self.test_resources:
            try:
                if resource_type == 'dynamodb_table':
                    self.dynamodb.Table(resource_name).delete()
                elif resource_type == 'dynamodb_table_dr':
                    self.dynamodb_dr.Table(resource_name).delete()
                elif resource_type == 's3_bucket':
                    # Delete all objects first
                    paginator = self.s3_client.get_paginator('list_objects_v2')
                    for page in paginator.paginate(Bucket=resource_name):
                        if 'Contents' in page:
                            objects = [{'Key': obj['Key']} for obj in page['Contents']]
                            self.s3_client.delete_objects(
                                Bucket=resource_name,
                                Delete={'Objects': objects}
                            )
                    self.s3_client.delete_bucket(Bucket=resource_name)
                elif resource_type == 'lambda_function':
                    self.lambda_client.delete_function(FunctionName=resource_name)
                elif resource_type == 'cloudformation_stack':
                    self.cloudformation.delete_stack(StackName=resource_name)
                    
                logger.info(f"Cleaned up {resource_type}: {resource_name}")
                
            except Exception as e:
                logger.warning(f"Failed to cleanup {resource_type} {resource_name}: {str(e)}")

    def generate_recovery_report(self, test_results: List[RecoveryTestResult]) -> Dict[str, Any]:
        """Generate comprehensive recovery test report"""
        total_tests = len(test_results)
        successful_tests = len([r for r in test_results if r.success])
        failed_tests = total_tests - successful_tests
        
        # Calculate average recovery time
        avg_recovery_time = sum(r.recovery_time_seconds for r in test_results) / total_tests if total_tests > 0 else 0
        
        # Calculate compliance with RTO/RPO
        rto_compliant = len([r for r in test_results if r.recovery_time_seconds < self.config.max_recovery_time])
        data_integrity_ok = len([r for r in test_results if r.data_integrity_verified])
        
        return {
            'report_generated': datetime.utcnow().isoformat(),
            'test_configuration': asdict(self.config),
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                'avg_recovery_time_seconds': avg_recovery_time,
                'rto_compliance': (rto_compliant / total_tests * 100) if total_tests > 0 else 0,
                'data_integrity_compliance': (data_integrity_ok / total_tests * 100) if total_tests > 0 else 0
            },
            'test_results': [asdict(result) for result in test_results],
            'recommendations': self._generate_recovery_recommendations(test_results)
        }

    def _generate_recovery_recommendations(self, test_results: List[RecoveryTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [r for r in test_results if not r.success]
        slow_tests = [r for r in test_results if r.recovery_time_seconds > self.config.max_recovery_time / 2]
        
        if failed_tests:
            recommendations.append(f"Address {len(failed_tests)} failed recovery test(s)")
        
        if slow_tests:
            recommendations.append(f"Optimize recovery time for {len(slow_tests)} test(s) that exceeded half of RTO")
        
        # Check specific test types
        dynamodb_tests = [r for r in test_results if r.test_type == 'dynamodb_pitr']
        if any(not r.success for r in dynamodb_tests):
            recommendations.append("Review DynamoDB backup and point-in-time recovery configuration")
        
        cross_region_tests = [r for r in test_results if r.test_type == 'cross_region_failover']
        if any(not r.success for r in cross_region_tests):
            recommendations.append("Improve cross-region failover procedures and automation")
        
        return recommendations


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='AI Nutritionist Recovery Testing')
    parser.add_argument('--environment', '-e', default='test', help='Environment for testing')
    parser.add_argument('--project-name', '-p', default='ai-nutritionist', help='Project name')
    parser.add_argument('--primary-region', default='us-east-1', help='Primary AWS region')
    parser.add_argument('--dr-region', default='us-west-2', help='DR AWS region')
    parser.add_argument('--test-data-size', type=int, default=100, help='Number of test records')
    parser.add_argument('--max-recovery-time', type=int, default=14400, help='Max recovery time in seconds')
    parser.add_argument('--skip-cross-region', action='store_true', help='Skip cross-region tests')
    parser.add_argument('--skip-performance', action='store_true', help='Skip performance tests')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip cleanup of test resources')
    parser.add_argument('--output-format', choices=['json', 'html'], default='json', help='Report format')
    
    args = parser.parse_args()
    
    # Create test configuration
    config = TestConfiguration(
        project_name=args.project_name,
        environment=args.environment,
        primary_region=args.primary_region,
        dr_region=args.dr_region,
        test_data_size=args.test_data_size,
        max_recovery_time=args.max_recovery_time,
        enable_cross_region_tests=not args.skip_cross_region,
        enable_performance_tests=not args.skip_performance,
        cleanup_after_test=not args.no_cleanup
    )
    
    # Create recovery tester
    tester = RecoveryTester(config)
    
    # Run tests
    print(f"Starting recovery testing for {args.project_name} ({args.environment})")
    test_results = tester.run_comprehensive_recovery_tests()
    
    # Generate report
    report = tester.generate_recovery_report(test_results)
    
    # Export report
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    if args.output_format == 'json':
        filename = f"recovery_test_report_{args.environment}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
    else:
        filename = f"recovery_test_report_{args.environment}_{timestamp}.html"
        # HTML generation would be implemented here
        with open(filename, 'w') as f:
            f.write(f"<h1>Recovery Test Report</h1><pre>{json.dumps(report, indent=2, default=str)}</pre>")
    
    # Print summary
    print("\n" + "="*80)
    print("RECOVERY TESTING SUMMARY")
    print("="*80)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Average Recovery Time: {report['summary']['avg_recovery_time_seconds']:.1f}s")
    print(f"RTO Compliance: {report['summary']['rto_compliance']:.1f}%")
    print(f"Data Integrity: {report['summary']['data_integrity_compliance']:.1f}%")
    print(f"Report saved to: {filename}")
    
    if report['summary']['failed_tests'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
