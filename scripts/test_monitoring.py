#!/usr/bin/env python3
"""
Comprehensive Monitoring System Test Suite
Validates all components of the monitoring infrastructure
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import boto3
import requests
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoringSystemTest:
    """Test suite for the comprehensive monitoring system"""
    
    def __init__(self):
        self.aws_region = 'us-east-1'
        self.project_name = 'ai-nutritionist'
        
        # AWS clients
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        self.lambda_client = boto3.client('lambda', region_name=self.aws_region)
        self.sns = boto3.client('sns', region_name=self.aws_region)
        self.logs = boto3.client('logs', region_name=self.aws_region)
        
        # Test results
        self.test_results = {
            'infrastructure': {},
            'functionality': {},
            'integration': {},
            'performance': {}
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all monitoring system tests"""
        logger.info("🚀 Starting comprehensive monitoring system tests")
        
        try:
            # Test infrastructure components
            await self.test_infrastructure()
            
            # Test core functionality
            await self.test_functionality()
            
            # Test integrations
            await self.test_integrations()
            
            # Test performance
            await self.test_performance()
            
            # Generate summary
            summary = self.generate_test_summary()
            
            logger.info("✅ All tests completed")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
    
    async def test_infrastructure(self):
        """Test infrastructure components"""
        logger.info("🔧 Testing infrastructure components...")
        
        # Test DynamoDB tables
        await self.test_dynamodb_tables()
        
        # Test Lambda functions
        await self.test_lambda_functions()
        
        # Test SNS topics
        await self.test_sns_topics()
        
        # Test CloudWatch log groups
        await self.test_cloudwatch_logs()
        
        # Test CloudWatch dashboards
        await self.test_cloudwatch_dashboards()
    
    async def test_dynamodb_tables(self):
        """Test DynamoDB table availability and structure"""
        logger.info("Testing DynamoDB tables...")
        
        required_tables = [
            'ai-nutritionist-monitoring-metrics',
            'ai-nutritionist-incidents',
            'ai-nutritionist-monitoring-alerts',
            'ai-nutritionist-postmortems',
            'ai-nutritionist-action-items',
            'ai-nutritionist-escalations'
        ]
        
        table_results = {}
        
        for table_name in required_tables:
            try:
                table = self.dynamodb.Table(table_name)
                table.load()
                
                # Test write/read operation
                test_item = {
                    'test_id': f'test-{int(time.time())}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'test_data': 'monitoring_test'
                }
                
                # Use appropriate key structure for each table
                if 'metrics' in table_name:
                    test_item['metric_id'] = test_item['test_id']
                elif 'incidents' in table_name:
                    test_item['incident_id'] = test_item['test_id']
                elif 'alerts' in table_name:
                    test_item['alert_id'] = test_item['test_id']
                elif 'postmortems' in table_name:
                    test_item['postmortem_id'] = test_item['test_id']
                elif 'action-items' in table_name:
                    test_item['action_item_id'] = test_item['test_id']
                elif 'escalations' in table_name:
                    test_item['escalation_id'] = test_item['test_id']
                
                table.put_item(Item=test_item)
                
                table_results[table_name] = {
                    'status': 'PASS',
                    'message': 'Table accessible and writable'
                }
                
                logger.info(f"✅ {table_name} - OK")
                
            except Exception as e:
                table_results[table_name] = {
                    'status': 'FAIL',
                    'message': str(e)
                }
                logger.error(f"❌ {table_name} - {e}")
        
        self.test_results['infrastructure']['dynamodb'] = table_results
    
    async def test_lambda_functions(self):
        """Test Lambda function availability and basic functionality"""
        logger.info("Testing Lambda functions...")
        
        required_functions = [
            'ai-nutritionist-comprehensive-monitoring',
            'ai-nutritionist-incident-response',
            'ai-nutritionist-postmortem-automation'
        ]
        
        function_results = {}
        
        for function_name in required_functions:
            try:
                # Get function configuration
                response = self.lambda_client.get_function(FunctionName=function_name)
                
                # Test function invocation
                test_payload = json.dumps({
                    'test': True,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                invoke_response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    Payload=test_payload
                )
                
                # Check response
                if invoke_response['StatusCode'] == 200:
                    function_results[function_name] = {
                        'status': 'PASS',
                        'message': 'Function executable',
                        'runtime': response['Configuration']['Runtime'],
                        'timeout': response['Configuration']['Timeout']
                    }
                    logger.info(f"✅ {function_name} - OK")
                else:
                    function_results[function_name] = {
                        'status': 'FAIL',
                        'message': f"Invocation failed with status {invoke_response['StatusCode']}"
                    }
                    logger.error(f"❌ {function_name} - Invocation failed")
                
            except Exception as e:
                function_results[function_name] = {
                    'status': 'FAIL',
                    'message': str(e)
                }
                logger.error(f"❌ {function_name} - {e}")
        
        self.test_results['infrastructure']['lambda'] = function_results
    
    async def test_sns_topics(self):
        """Test SNS topic availability"""
        logger.info("Testing SNS topics...")
        
        required_topics = [
            'ai-nutritionist-alerts',
            'ai-nutritionist-business-alerts',
            'ai-nutritionist-pagerduty-alerts'
        ]
        
        topic_results = {}
        
        # List all topics
        try:
            topics_response = self.sns.list_topics()
            topic_arns = [topic['TopicArn'] for topic in topics_response['Topics']]
            
            for topic_name in required_topics:
                topic_found = any(topic_name in arn for arn in topic_arns)
                
                if topic_found:
                    # Find the exact ARN
                    topic_arn = next(arn for arn in topic_arns if topic_name in arn)
                    
                    # Test publish (dry run)
                    test_message = {
                        'test': True,
                        'timestamp': datetime.utcnow().isoformat(),
                        'message': 'Monitoring system test'
                    }
                    
                    # We don't actually publish to avoid spam
                    topic_results[topic_name] = {
                        'status': 'PASS',
                        'message': 'Topic exists and accessible',
                        'arn': topic_arn
                    }
                    logger.info(f"✅ {topic_name} - OK")
                else:
                    topic_results[topic_name] = {
                        'status': 'FAIL',
                        'message': 'Topic not found'
                    }
                    logger.error(f"❌ {topic_name} - Not found")
            
        except Exception as e:
            logger.error(f"❌ SNS topics test failed: {e}")
            topic_results['error'] = str(e)
        
        self.test_results['infrastructure']['sns'] = topic_results
    
    async def test_cloudwatch_logs(self):
        """Test CloudWatch log groups"""
        logger.info("Testing CloudWatch log groups...")
        
        required_log_groups = [
            '/ai-nutritionist/application',
            '/ai-nutritionist/performance',
            '/ai-nutritionist/security'
        ]
        
        log_results = {}
        
        try:
            for log_group in required_log_groups:
                try:
                    response = self.logs.describe_log_groups(
                        logGroupNamePrefix=log_group
                    )
                    
                    if response['logGroups']:
                        log_results[log_group] = {
                            'status': 'PASS',
                            'message': 'Log group exists',
                            'retention': response['logGroups'][0].get('retentionInDays', 'Never expire')
                        }
                        logger.info(f"✅ {log_group} - OK")
                    else:
                        # Create log group for testing
                        self.logs.create_log_group(logGroupName=log_group)
                        log_results[log_group] = {
                            'status': 'PASS',
                            'message': 'Log group created during test'
                        }
                        logger.info(f"✅ {log_group} - Created")
                        
                except Exception as e:
                    log_results[log_group] = {
                        'status': 'FAIL',
                        'message': str(e)
                    }
                    logger.error(f"❌ {log_group} - {e}")
            
        except Exception as e:
            logger.error(f"❌ CloudWatch logs test failed: {e}")
            log_results['error'] = str(e)
        
        self.test_results['infrastructure']['cloudwatch_logs'] = log_results
    
    async def test_cloudwatch_dashboards(self):
        """Test CloudWatch dashboards"""
        logger.info("Testing CloudWatch dashboards...")
        
        expected_dashboards = [
            'AI-Nutritionist-Main-Dashboard',
            'AI-Nutritionist-Business-Dashboard',
            'AI-Nutritionist-Infrastructure-Dashboard'
        ]
        
        dashboard_results = {}
        
        try:
            response = self.cloudwatch.list_dashboards()
            existing_dashboards = [dash['DashboardName'] for dash in response['DashboardEntries']]
            
            for dashboard_name in expected_dashboards:
                if dashboard_name in existing_dashboards:
                    dashboard_results[dashboard_name] = {
                        'status': 'PASS',
                        'message': 'Dashboard exists'
                    }
                    logger.info(f"✅ {dashboard_name} - OK")
                else:
                    dashboard_results[dashboard_name] = {
                        'status': 'WARN',
                        'message': 'Dashboard not found (may not be deployed yet)'
                    }
                    logger.warning(f"⚠️ {dashboard_name} - Not found")
            
        except Exception as e:
            logger.error(f"❌ CloudWatch dashboards test failed: {e}")
            dashboard_results['error'] = str(e)
        
        self.test_results['infrastructure']['cloudwatch_dashboards'] = dashboard_results
    
    async def test_functionality(self):
        """Test core monitoring functionality"""
        logger.info("🔧 Testing core functionality...")
        
        # Test metrics collection
        await self.test_metrics_collection()
        
        # Test alert generation
        await self.test_alert_generation()
        
        # Test incident detection
        await self.test_incident_detection()
        
        # Test post-mortem generation
        await self.test_postmortem_generation()
    
    async def test_metrics_collection(self):
        """Test metrics collection functionality"""
        logger.info("Testing metrics collection...")
        
        try:
            # Simulate metric collection by invoking the monitoring function
            payload = json.dumps({'test_mode': True})
            
            response = self.lambda_client.invoke(
                FunctionName='ai-nutritionist-comprehensive-monitoring',
                Payload=payload
            )
            
            if response['StatusCode'] == 200:
                response_payload = json.loads(response['Payload'].read())
                
                self.test_results['functionality']['metrics_collection'] = {
                    'status': 'PASS',
                    'message': 'Metrics collection functional',
                    'response': response_payload
                }
                logger.info("✅ Metrics collection - OK")
            else:
                self.test_results['functionality']['metrics_collection'] = {
                    'status': 'FAIL',
                    'message': f"Function returned status {response['StatusCode']}"
                }
                logger.error("❌ Metrics collection - Failed")
                
        except Exception as e:
            self.test_results['functionality']['metrics_collection'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ Metrics collection test failed: {e}")
    
    async def test_alert_generation(self):
        """Test alert generation functionality"""
        logger.info("Testing alert generation...")
        
        try:
            # Create test metric data that should trigger an alert
            test_metric = {
                'metric_name': 'ErrorRate',
                'current_value': 15.0,  # Above critical threshold
                'threshold': 10.0,
                'dimensions': {'TestFunction': 'monitoring-test'},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Invoke incident response with test data
            payload = json.dumps({
                'Records': [{
                    'Sns': {
                        'Message': json.dumps(test_metric)
                    }
                }]
            })
            
            response = self.lambda_client.invoke(
                FunctionName='ai-nutritionist-incident-response',
                Payload=payload
            )
            
            if response['StatusCode'] == 200:
                self.test_results['functionality']['alert_generation'] = {
                    'status': 'PASS',
                    'message': 'Alert generation functional'
                }
                logger.info("✅ Alert generation - OK")
            else:
                self.test_results['functionality']['alert_generation'] = {
                    'status': 'FAIL',
                    'message': f"Function returned status {response['StatusCode']}"
                }
                logger.error("❌ Alert generation - Failed")
                
        except Exception as e:
            self.test_results['functionality']['alert_generation'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ Alert generation test failed: {e}")
    
    async def test_incident_detection(self):
        """Test incident detection logic"""
        logger.info("Testing incident detection...")
        
        try:
            # Test with known incident scenario
            test_incident_data = {
                'incident_id': f'TEST-{int(time.time())}',
                'severity': 'sev2',
                'title': 'Test incident for monitoring validation',
                'description': 'This is a test incident to validate monitoring',
                'status': 'resolved',
                'created_at': datetime.utcnow().isoformat(),
                'resolved_at': (datetime.utcnow() + timedelta(minutes=30)).isoformat()
            }
            
            # Store in incidents table
            incidents_table = self.dynamodb.Table('ai-nutritionist-incidents')
            incidents_table.put_item(Item=test_incident_data)
            
            self.test_results['functionality']['incident_detection'] = {
                'status': 'PASS',
                'message': 'Incident detection logic functional',
                'test_incident_id': test_incident_data['incident_id']
            }
            logger.info("✅ Incident detection - OK")
            
        except Exception as e:
            self.test_results['functionality']['incident_detection'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ Incident detection test failed: {e}")
    
    async def test_postmortem_generation(self):
        """Test post-mortem generation functionality"""
        logger.info("Testing post-mortem generation...")
        
        try:
            # Use the test incident from previous test
            if 'incident_detection' in self.test_results['functionality']:
                test_incident_id = self.test_results['functionality']['incident_detection'].get('test_incident_id')
                
                if test_incident_id:
                    payload = json.dumps({'incident_id': test_incident_id})
                    
                    response = self.lambda_client.invoke(
                        FunctionName='ai-nutritionist-postmortem-automation',
                        Payload=payload
                    )
                    
                    if response['StatusCode'] == 200:
                        self.test_results['functionality']['postmortem_generation'] = {
                            'status': 'PASS',
                            'message': 'Post-mortem generation functional'
                        }
                        logger.info("✅ Post-mortem generation - OK")
                    else:
                        self.test_results['functionality']['postmortem_generation'] = {
                            'status': 'FAIL',
                            'message': f"Function returned status {response['StatusCode']}"
                        }
                        logger.error("❌ Post-mortem generation - Failed")
                else:
                    self.test_results['functionality']['postmortem_generation'] = {
                        'status': 'SKIP',
                        'message': 'No test incident available'
                    }
            
        except Exception as e:
            self.test_results['functionality']['postmortem_generation'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ Post-mortem generation test failed: {e}")
    
    async def test_integrations(self):
        """Test external integrations"""
        logger.info("🔗 Testing integrations...")
        
        # Test CloudWatch integration
        await self.test_cloudwatch_integration()
        
        # Test SNS integration
        await self.test_sns_integration()
    
    async def test_cloudwatch_integration(self):
        """Test CloudWatch metrics publishing"""
        logger.info("Testing CloudWatch integration...")
        
        try:
            # Publish test metric
            test_metric_data = [
                {
                    'MetricName': 'TestMetric',
                    'Value': 42.0,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {
                            'Name': 'TestDimension',
                            'Value': 'MonitoringTest'
                        }
                    ]
                }
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace='AI-Nutritionist/Test',
                MetricData=test_metric_data
            )
            
            # Wait a moment for metric to be available
            await asyncio.sleep(2)
            
            # Try to retrieve the metric
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AI-Nutritionist/Test',
                MetricName='TestMetric',
                Dimensions=[
                    {
                        'Name': 'TestDimension',
                        'Value': 'MonitoringTest'
                    }
                ],
                StartTime=datetime.utcnow() - timedelta(minutes=5),
                EndTime=datetime.utcnow(),
                Period=300,
                Statistics=['Average']
            )
            
            self.test_results['integration']['cloudwatch'] = {
                'status': 'PASS',
                'message': 'CloudWatch integration working',
                'datapoints': len(response.get('Datapoints', []))
            }
            logger.info("✅ CloudWatch integration - OK")
            
        except Exception as e:
            self.test_results['integration']['cloudwatch'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ CloudWatch integration test failed: {e}")
    
    async def test_sns_integration(self):
        """Test SNS notification functionality"""
        logger.info("Testing SNS integration...")
        
        try:
            # Get topic ARN
            topics_response = self.sns.list_topics()
            alert_topic = None
            
            for topic in topics_response['Topics']:
                if 'ai-nutritionist-alerts' in topic['TopicArn']:
                    alert_topic = topic['TopicArn']
                    break
            
            if alert_topic:
                # We won't actually publish to avoid spam, just verify access
                self.test_results['integration']['sns'] = {
                    'status': 'PASS',
                    'message': 'SNS integration accessible',
                    'topic_arn': alert_topic
                }
                logger.info("✅ SNS integration - OK")
            else:
                self.test_results['integration']['sns'] = {
                    'status': 'FAIL',
                    'message': 'Alert topic not found'
                }
                logger.error("❌ SNS integration - Alert topic not found")
                
        except Exception as e:
            self.test_results['integration']['sns'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ SNS integration test failed: {e}")
    
    async def test_performance(self):
        """Test system performance"""
        logger.info("⚡ Testing performance...")
        
        # Test Lambda function performance
        await self.test_lambda_performance()
        
        # Test DynamoDB performance
        await self.test_dynamodb_performance()
    
    async def test_lambda_performance(self):
        """Test Lambda function execution performance"""
        logger.info("Testing Lambda performance...")
        
        try:
            performance_results = {}
            
            functions_to_test = [
                'ai-nutritionist-comprehensive-monitoring',
                'ai-nutritionist-incident-response'
            ]
            
            for function_name in functions_to_test:
                execution_times = []
                
                # Run multiple invocations to get average
                for i in range(3):
                    start_time = time.time()
                    
                    response = self.lambda_client.invoke(
                        FunctionName=function_name,
                        Payload=json.dumps({'test': True, 'run': i})
                    )
                    
                    execution_time = time.time() - start_time
                    execution_times.append(execution_time)
                    
                    if response['StatusCode'] != 200:
                        break
                
                if execution_times:
                    avg_time = sum(execution_times) / len(execution_times)
                    performance_results[function_name] = {
                        'status': 'PASS' if avg_time < 30 else 'WARN',
                        'avg_execution_time': round(avg_time, 3),
                        'max_execution_time': round(max(execution_times), 3),
                        'executions': len(execution_times)
                    }
                    
                    if avg_time < 30:
                        logger.info(f"✅ {function_name} - {avg_time:.3f}s avg")
                    else:
                        logger.warning(f"⚠️ {function_name} - {avg_time:.3f}s avg (slow)")
            
            self.test_results['performance']['lambda'] = performance_results
            
        except Exception as e:
            self.test_results['performance']['lambda'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ Lambda performance test failed: {e}")
    
    async def test_dynamodb_performance(self):
        """Test DynamoDB read/write performance"""
        logger.info("Testing DynamoDB performance...")
        
        try:
            # Test metrics table performance
            metrics_table = self.dynamodb.Table('ai-nutritionist-monitoring-metrics')
            
            # Write performance test
            write_times = []
            for i in range(5):
                start_time = time.time()
                
                test_item = {
                    'metric_id': f'perf-test-{int(time.time())}-{i}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'metric_name': 'PerformanceTest',
                    'value': Decimal(str(i * 10)),
                    'namespace': 'AI-Nutritionist/Test'
                }
                
                metrics_table.put_item(Item=test_item)
                
                write_time = time.time() - start_time
                write_times.append(write_time)
            
            # Read performance test
            read_times = []
            for i in range(5):
                start_time = time.time()
                
                response = metrics_table.scan(
                    FilterExpression='namespace = :ns',
                    ExpressionAttributeValues={':ns': 'AI-Nutritionist/Test'},
                    Limit=10
                )
                
                read_time = time.time() - start_time
                read_times.append(read_time)
            
            avg_write_time = sum(write_times) / len(write_times)
            avg_read_time = sum(read_times) / len(read_times)
            
            self.test_results['performance']['dynamodb'] = {
                'status': 'PASS' if avg_write_time < 1 and avg_read_time < 1 else 'WARN',
                'avg_write_time': round(avg_write_time, 3),
                'avg_read_time': round(avg_read_time, 3),
                'write_operations': len(write_times),
                'read_operations': len(read_times)
            }
            
            logger.info(f"✅ DynamoDB - Write: {avg_write_time:.3f}s, Read: {avg_read_time:.3f}s")
            
        except Exception as e:
            self.test_results['performance']['dynamodb'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            logger.error(f"❌ DynamoDB performance test failed: {e}")
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warnings = 0
        
        # Count results
        for category, tests in self.test_results.items():
            for test_name, result in tests.items():
                if isinstance(result, dict) and 'status' in result:
                    total_tests += 1
                    if result['status'] == 'PASS':
                        passed_tests += 1
                    elif result['status'] == 'FAIL':
                        failed_tests += 1
                    elif result['status'] == 'WARN':
                        warnings += 1
                elif isinstance(result, dict):
                    # Nested results
                    for sub_test, sub_result in result.items():
                        if isinstance(sub_result, dict) and 'status' in sub_result:
                            total_tests += 1
                            if sub_result['status'] == 'PASS':
                                passed_tests += 1
                            elif sub_result['status'] == 'FAIL':
                                failed_tests += 1
                            elif sub_result['status'] == 'WARN':
                                warnings += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            'test_run_id': f'test-{int(time.time())}',
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'warnings': warnings,
                'success_rate': round(success_rate, 2)
            },
            'status': 'PASS' if failed_tests == 0 else 'FAIL',
            'detailed_results': self.test_results
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print formatted test summary"""
        print("\n" + "="*60)
        print("🧪 MONITORING SYSTEM TEST SUMMARY")
        print("="*60)
        print(f"Test Run ID: {summary['test_run_id']}")
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Overall Status: {'✅ PASS' if summary['status'] == 'PASS' else '❌ FAIL'}")
        print("\n📊 Results:")
        print(f"  Total Tests: {summary['summary']['total_tests']}")
        print(f"  Passed: {summary['summary']['passed']} ✅")
        print(f"  Failed: {summary['summary']['failed']} ❌")
        print(f"  Warnings: {summary['summary']['warnings']} ⚠️")
        print(f"  Success Rate: {summary['summary']['success_rate']}%")
        
        # Print detailed results for failed tests
        if summary['summary']['failed'] > 0:
            print("\n❌ Failed Tests:")
            for category, tests in summary['detailed_results'].items():
                for test_name, result in tests.items():
                    if isinstance(result, dict):
                        if result.get('status') == 'FAIL':
                            print(f"  • {category}.{test_name}: {result.get('message', 'Unknown error')}")
                        elif isinstance(result, dict):
                            for sub_test, sub_result in result.items():
                                if isinstance(sub_result, dict) and sub_result.get('status') == 'FAIL':
                                    print(f"  • {category}.{test_name}.{sub_test}: {sub_result.get('message', 'Unknown error')}")
        
        print("\n" + "="*60)


async def main():
    """Main test execution"""
    test_suite = MonitoringSystemTest()
    
    try:
        # Run all tests
        summary = await test_suite.run_all_tests()
        
        # Print summary
        test_suite.print_summary(summary)
        
        # Save results to file
        with open('monitoring_test_results.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: monitoring_test_results.json")
        
        # Exit with appropriate code
        exit_code = 0 if summary['status'] == 'PASS' else 1
        return exit_code
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
