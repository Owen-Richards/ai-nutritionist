#!/usr/bin/env python3
"""
Backup Cost Optimization System for AI Nutritionist Application

This script provides comprehensive backup cost optimization capabilities:
- Cost analysis and tracking
- Storage lifecycle optimization
- Intelligent backup scheduling
- Cost prediction and budgeting
- Automated cost alerts
- Backup storage optimization

Author: AI Nutritionist DevOps Team
Version: 1.0.0
"""

import os
import sys
import json
import boto3
import logging
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
class BackupCostAnalysis:
    """Backup cost analysis result"""
    resource_type: str
    resource_name: str
    current_monthly_cost: float
    optimized_monthly_cost: float
    potential_savings: float
    savings_percentage: float
    optimization_recommendations: List[str]
    storage_breakdown: Dict[str, float]
    lifecycle_optimization: Dict[str, Any]


@dataclass
class CostOptimizationConfig:
    """Configuration for cost optimization"""
    project_name: str = "ai-nutritionist"
    environment: str = "prod"
    aws_region: str = "us-east-1"
    analysis_period_days: int = 30
    target_savings_percentage: float = 20.0
    enable_automated_optimization: bool = False
    notification_threshold: float = 100.0  # Monthly cost threshold for alerts


class BackupCostOptimizer:
    """Comprehensive backup cost optimization system"""

    def __init__(self, config: CostOptimizationConfig):
        self.config = config
        
        # AWS service clients
        self.cost_explorer = boto3.client('ce', region_name='us-east-1')  # Cost Explorer only in us-east-1
        self.backup_client = boto3.client('backup', region_name=config.aws_region)
        self.s3_client = boto3.client('s3', region_name=config.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=config.aws_region)
        self.sns_client = boto3.client('sns', region_name=config.aws_region)
        
        # Cost tracking
        self.current_costs = {}
        self.optimization_opportunities = []

    def analyze_backup_costs(self) -> Dict[str, Any]:
        """Analyze current backup costs and identify optimization opportunities"""
        logger.info("Starting comprehensive backup cost analysis")
        
        analysis_results = {
            'analysis_date': datetime.utcnow().isoformat(),
            'period_days': self.config.analysis_period_days,
            'total_current_cost': 0.0,
            'total_optimized_cost': 0.0,
            'total_potential_savings': 0.0,
            'cost_breakdown': {},
            'optimization_recommendations': [],
            'detailed_analysis': []
        }
        
        try:
            # 1. Analyze AWS Backup costs
            backup_analysis = self._analyze_aws_backup_costs()
            analysis_results['detailed_analysis'].extend(backup_analysis)
            
            # 2. Analyze S3 storage costs
            s3_analysis = self._analyze_s3_backup_costs()
            analysis_results['detailed_analysis'].extend(s3_analysis)
            
            # 3. Analyze DynamoDB backup costs
            dynamodb_analysis = self._analyze_dynamodb_backup_costs()
            analysis_results['detailed_analysis'].extend(dynamodb_analysis)
            
            # 4. Calculate totals
            for analysis in analysis_results['detailed_analysis']:
                analysis_results['total_current_cost'] += analysis.current_monthly_cost
                analysis_results['total_optimized_cost'] += analysis.optimized_monthly_cost
                analysis_results['total_potential_savings'] += analysis.potential_savings
            
            # 5. Generate overall recommendations
            analysis_results['optimization_recommendations'] = self._generate_cost_optimization_recommendations(
                analysis_results['detailed_analysis']
            )
            
            # 6. Create cost breakdown
            analysis_results['cost_breakdown'] = self._create_cost_breakdown(
                analysis_results['detailed_analysis']
            )
            
            logger.info(f"Cost analysis completed. Current: ${analysis_results['total_current_cost']:.2f}, "
                       f"Optimized: ${analysis_results['total_optimized_cost']:.2f}, "
                       f"Savings: ${analysis_results['total_potential_savings']:.2f}")
            
        except Exception as e:
            logger.error(f"Error during cost analysis: {str(e)}")
            analysis_results['error'] = str(e)
        
        return analysis_results

    def _analyze_aws_backup_costs(self) -> List[BackupCostAnalysis]:
        """Analyze AWS Backup service costs"""
        logger.info("Analyzing AWS Backup costs")
        analyses = []
        
        try:
            # Get backup vault information
            backup_vault = f"{self.config.project_name}-backup-vault-{self.config.environment}"
            
            # Get recovery points
            paginator = self.backup_client.get_paginator('list_recovery_points_by_backup_vault')
            total_backup_size = 0
            backup_count = 0
            
            for page in paginator.paginate(BackupVaultName=backup_vault):
                for recovery_point in page['RecoveryPoints']:
                    backup_size = recovery_point.get('BackupSizeInBytes', 0)
                    total_backup_size += backup_size
                    backup_count += 1
            
            # Convert to GB
            total_size_gb = total_backup_size / (1024**3)
            
            # Calculate current costs (AWS Backup pricing)
            storage_cost_per_gb = 0.05  # $0.05 per GB per month
            current_monthly_cost = total_size_gb * storage_cost_per_gb
            
            # Calculate optimized costs with lifecycle policies
            optimized_cost = self._calculate_optimized_backup_cost(total_size_gb, backup_count)
            potential_savings = current_monthly_cost - optimized_cost
            savings_percentage = (potential_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0
            
            # Generate recommendations
            recommendations = []
            if total_size_gb > 100:  # If more than 100GB
                recommendations.append("Implement lifecycle policies to move old backups to cold storage")
            if backup_count > 50:
                recommendations.append("Review backup retention policies to reduce unnecessary backups")
            if savings_percentage > 10:
                recommendations.append("Enable automated backup lifecycle management")
            
            analysis = BackupCostAnalysis(
                resource_type="AWS Backup",
                resource_name=backup_vault,
                current_monthly_cost=current_monthly_cost,
                optimized_monthly_cost=optimized_cost,
                potential_savings=potential_savings,
                savings_percentage=savings_percentage,
                optimization_recommendations=recommendations,
                storage_breakdown={
                    "standard_storage_gb": total_size_gb,
                    "cold_storage_gb": 0,
                    "total_backups": backup_count
                },
                lifecycle_optimization=self._design_backup_lifecycle_policy(total_size_gb, backup_count)
            )
            
            analyses.append(analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing AWS Backup costs: {str(e)}")
        
        return analyses

    def _analyze_s3_backup_costs(self) -> List[BackupCostAnalysis]:
        """Analyze S3 backup storage costs"""
        logger.info("Analyzing S3 backup costs")
        analyses = []
        
        try:
            # List all S3 buckets related to backups
            response = self.s3_client.list_buckets()
            
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                
                # Filter for backup-related buckets
                if (self.config.project_name in bucket_name and 
                    any(keyword in bucket_name.lower() for keyword in ['backup', 'snapshot', 'archive'])):
                    
                    analysis = self._analyze_s3_bucket_costs(bucket_name)
                    if analysis:
                        analyses.append(analysis)
        
        except Exception as e:
            logger.error(f"Error analyzing S3 backup costs: {str(e)}")
        
        return analyses

    def _analyze_s3_bucket_costs(self, bucket_name: str) -> Optional[BackupCostAnalysis]:
        """Analyze costs for a specific S3 bucket"""
        try:
            # Get bucket size and object count
            total_size = 0
            object_count = 0
            storage_classes = {}
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        object_count += 1
                        
                        storage_class = obj.get('StorageClass', 'STANDARD')
                        storage_classes[storage_class] = storage_classes.get(storage_class, 0) + obj['Size']
            
            if total_size == 0:
                return None
            
            # Convert to GB
            total_size_gb = total_size / (1024**3)
            
            # Calculate current costs based on storage classes
            current_monthly_cost = self._calculate_s3_storage_cost(storage_classes)
            
            # Calculate optimized costs with intelligent tiering
            optimized_cost = self._calculate_optimized_s3_cost(total_size_gb, object_count)
            potential_savings = current_monthly_cost - optimized_cost
            savings_percentage = (potential_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0
            
            # Generate recommendations
            recommendations = []
            if storage_classes.get('STANDARD', 0) > total_size * 0.5:
                recommendations.append("Enable S3 Intelligent Tiering for automatic cost optimization")
            if total_size_gb > 50:
                recommendations.append("Implement lifecycle policies to transition to cheaper storage classes")
            if object_count > 1000:
                recommendations.append("Consider using S3 Batch Operations for bulk lifecycle transitions")
            
            return BackupCostAnalysis(
                resource_type="S3 Backup Storage",
                resource_name=bucket_name,
                current_monthly_cost=current_monthly_cost,
                optimized_monthly_cost=optimized_cost,
                potential_savings=potential_savings,
                savings_percentage=savings_percentage,
                optimization_recommendations=recommendations,
                storage_breakdown={
                    "total_size_gb": total_size_gb,
                    "object_count": object_count,
                    "storage_classes": {k: v/(1024**3) for k, v in storage_classes.items()}
                },
                lifecycle_optimization=self._design_s3_lifecycle_policy(storage_classes, total_size_gb)
            )
            
        except Exception as e:
            logger.error(f"Error analyzing S3 bucket {bucket_name}: {str(e)}")
            return None

    def _analyze_dynamodb_backup_costs(self) -> List[BackupCostAnalysis]:
        """Analyze DynamoDB backup costs"""
        logger.info("Analyzing DynamoDB backup costs")
        analyses = []
        
        try:
            # List DynamoDB tables
            paginator = self.dynamodb.meta.client.get_paginator('list_tables')
            
            for page in paginator.paginate():
                for table_name in page['TableNames']:
                    if self.config.project_name in table_name and self.config.environment in table_name:
                        analysis = self._analyze_dynamodb_table_backup_costs(table_name)
                        if analysis:
                            analyses.append(analysis)
        
        except Exception as e:
            logger.error(f"Error analyzing DynamoDB backup costs: {str(e)}")
        
        return analyses

    def _analyze_dynamodb_table_backup_costs(self, table_name: str) -> Optional[BackupCostAnalysis]:
        """Analyze backup costs for a specific DynamoDB table"""
        try:
            # Get table information
            table_response = self.dynamodb.meta.client.describe_table(TableName=table_name)
            table_size_bytes = table_response['Table'].get('TableSizeBytes', 0)
            table_size_gb = table_size_bytes / (1024**3)
            
            # Check if continuous backups are enabled
            continuous_backups = self.dynamodb.meta.client.describe_continuous_backups(TableName=table_name)
            pitr_enabled = continuous_backups['ContinuousBackupsDescription']['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus'] == 'ENABLED'
            
            if not pitr_enabled:
                return None
            
            # Calculate backup costs
            # DynamoDB continuous backups are typically charged at $0.20 per GB per month
            backup_cost_per_gb = 0.20
            current_monthly_cost = table_size_gb * backup_cost_per_gb
            
            # Optimized cost (with retention optimization)
            optimized_cost = current_monthly_cost * 0.8  # Assume 20% savings with optimization
            potential_savings = current_monthly_cost - optimized_cost
            savings_percentage = 20.0
            
            # Generate recommendations
            recommendations = []
            if table_size_gb > 10:
                recommendations.append("Review point-in-time recovery retention period")
            recommendations.append("Consider using on-demand backups for less critical data")
            if table_size_gb > 100:
                recommendations.append("Implement data archiving strategy for old records")
            
            return BackupCostAnalysis(
                resource_type="DynamoDB Backup",
                resource_name=table_name,
                current_monthly_cost=current_monthly_cost,
                optimized_monthly_cost=optimized_cost,
                potential_savings=potential_savings,
                savings_percentage=savings_percentage,
                optimization_recommendations=recommendations,
                storage_breakdown={
                    "table_size_gb": table_size_gb,
                    "pitr_enabled": pitr_enabled,
                    "backup_type": "continuous"
                },
                lifecycle_optimization={
                    "retention_optimization": "Reduce retention from 35 to 7 days for non-critical tables",
                    "archival_strategy": "Archive data older than 1 year"
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing DynamoDB table {table_name}: {str(e)}")
            return None

    def _calculate_optimized_backup_cost(self, total_size_gb: float, backup_count: int) -> float:
        """Calculate optimized backup cost with lifecycle policies"""
        # Assume lifecycle policy: 30 days standard, 60 days IA, rest in Glacier
        if backup_count < 30:
            return total_size_gb * 0.05  # All in standard
        
        # Distribute across storage tiers
        standard_portion = min(30, backup_count) / backup_count
        ia_portion = min(60, max(0, backup_count - 30)) / backup_count
        glacier_portion = max(0, backup_count - 90) / backup_count
        
        standard_cost = total_size_gb * standard_portion * 0.05
        ia_cost = total_size_gb * ia_portion * 0.0125
        glacier_cost = total_size_gb * glacier_portion * 0.004
        
        return standard_cost + ia_cost + glacier_cost

    def _calculate_s3_storage_cost(self, storage_classes: Dict[str, int]) -> float:
        """Calculate S3 storage cost based on storage classes"""
        # S3 pricing per GB per month
        pricing = {
            'STANDARD': 0.023,
            'STANDARD_IA': 0.0125,
            'ONEZONE_IA': 0.01,
            'GLACIER': 0.004,
            'DEEP_ARCHIVE': 0.00099
        }
        
        total_cost = 0.0
        for storage_class, size_bytes in storage_classes.items():
            size_gb = size_bytes / (1024**3)
            cost_per_gb = pricing.get(storage_class, pricing['STANDARD'])
            total_cost += size_gb * cost_per_gb
        
        return total_cost

    def _calculate_optimized_s3_cost(self, total_size_gb: float, object_count: int) -> float:
        """Calculate optimized S3 cost with intelligent tiering"""
        # Assume intelligent tiering saves 20-30% on average
        base_cost = total_size_gb * 0.023  # Standard pricing
        intelligent_tiering_savings = 0.25
        monitoring_cost = object_count * 0.0025 / 1000  # $0.0025 per 1000 objects
        
        optimized_cost = base_cost * (1 - intelligent_tiering_savings) + monitoring_cost
        return optimized_cost

    def _design_backup_lifecycle_policy(self, total_size_gb: float, backup_count: int) -> Dict[str, Any]:
        """Design optimal backup lifecycle policy"""
        return {
            "transition_to_ia": 30,  # days
            "transition_to_glacier": 90,  # days
            "delete_after": 365,  # days
            "estimated_distribution": {
                "standard": f"{min(30, backup_count)} backups",
                "ia": f"{min(60, max(0, backup_count - 30))} backups",
                "glacier": f"{max(0, backup_count - 90)} backups"
            },
            "cost_impact": "30-50% reduction in storage costs"
        }

    def _design_s3_lifecycle_policy(self, storage_classes: Dict[str, int], total_size_gb: float) -> Dict[str, Any]:
        """Design optimal S3 lifecycle policy"""
        return {
            "current_access_pattern": "Most data in STANDARD storage",
            "recommended_policy": {
                "transition_to_ia": 30,
                "transition_to_glacier": 90,
                "transition_to_deep_archive": 365,
                "enable_intelligent_tiering": True
            },
            "expected_savings": "20-40% reduction in storage costs",
            "implementation": "CloudFormation template with lifecycle rules"
        }

    def _generate_cost_optimization_recommendations(self, analyses: List[BackupCostAnalysis]) -> List[str]:
        """Generate overall cost optimization recommendations"""
        recommendations = []
        
        total_savings = sum(analysis.potential_savings for analysis in analyses)
        
        if total_savings > 50:
            recommendations.append(f"Implement all optimizations to save ${total_savings:.2f} per month")
        
        # High-impact recommendations
        high_cost_resources = [a for a in analyses if a.current_monthly_cost > 100]
        if high_cost_resources:
            recommendations.append("Focus on optimizing high-cost resources first for maximum impact")
        
        # Storage class optimization
        s3_analyses = [a for a in analyses if a.resource_type == "S3 Backup Storage"]
        if s3_analyses:
            recommendations.append("Enable S3 Intelligent Tiering for automatic cost optimization")
        
        # Backup retention optimization
        if any("retention" in str(a.optimization_recommendations) for a in analyses):
            recommendations.append("Review and optimize backup retention policies across all services")
        
        # Automation recommendations
        if total_savings > 20:
            recommendations.append("Implement automated cost optimization policies")
        
        return recommendations

    def _create_cost_breakdown(self, analyses: List[BackupCostAnalysis]) -> Dict[str, float]:
        """Create cost breakdown by resource type"""
        breakdown = {}
        
        for analysis in analyses:
            resource_type = analysis.resource_type
            if resource_type not in breakdown:
                breakdown[resource_type] = {
                    'current_cost': 0.0,
                    'optimized_cost': 0.0,
                    'potential_savings': 0.0,
                    'resource_count': 0
                }
            
            breakdown[resource_type]['current_cost'] += analysis.current_monthly_cost
            breakdown[resource_type]['optimized_cost'] += analysis.optimized_monthly_cost
            breakdown[resource_type]['potential_savings'] += analysis.potential_savings
            breakdown[resource_type]['resource_count'] += 1
        
        return breakdown

    def implement_cost_optimizations(self, analysis_result: Dict[str, Any], 
                                   optimization_types: List[str] = None) -> Dict[str, Any]:
        """Implement cost optimization recommendations"""
        logger.info("Implementing cost optimizations")
        
        if optimization_types is None:
            optimization_types = ['s3_lifecycle', 'backup_lifecycle', 'retention_policies']
        
        implementation_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'optimization_types': optimization_types,
            'implemented_optimizations': [],
            'errors': [],
            'estimated_monthly_savings': 0.0
        }
        
        try:
            for analysis in analysis_result['detailed_analysis']:
                if 's3_lifecycle' in optimization_types and analysis['resource_type'] == 'S3 Backup Storage':
                    result = self._implement_s3_lifecycle_optimization(analysis)
                    implementation_results['implemented_optimizations'].append(result)
                
                if 'backup_lifecycle' in optimization_types and analysis['resource_type'] == 'AWS Backup':
                    result = self._implement_backup_lifecycle_optimization(analysis)
                    implementation_results['implemented_optimizations'].append(result)
                
                if 'retention_policies' in optimization_types:
                    result = self._implement_retention_optimization(analysis)
                    implementation_results['implemented_optimizations'].append(result)
            
            # Calculate total estimated savings
            implementation_results['estimated_monthly_savings'] = sum(
                opt.get('estimated_savings', 0) for opt in implementation_results['implemented_optimizations']
            )
            
        except Exception as e:
            logger.error(f"Error implementing optimizations: {str(e)}")
            implementation_results['errors'].append(str(e))
        
        return implementation_results

    def _implement_s3_lifecycle_optimization(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Implement S3 lifecycle policy optimization"""
        bucket_name = analysis['resource_name']
        
        try:
            # Create lifecycle configuration
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'BackupOptimization',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'DEEP_ARCHIVE'
                            }
                        ]
                    }
                ]
            }
            
            # Apply lifecycle policy
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            
            # Enable intelligent tiering
            intelligent_tiering_config = {
                'Id': 'IntelligentTiering',
                'Status': 'Enabled',
                'Filter': {'Prefix': ''},
                'Tiering': {
                    'Days': 0,
                    'AccessTier': 'ARCHIVE_ACCESS'
                }
            }
            
            try:
                self.s3_client.put_bucket_intelligent_tiering_configuration(
                    Bucket=bucket_name,
                    Id='IntelligentTiering',
                    IntelligentTieringConfiguration=intelligent_tiering_config
                )
            except Exception as e:
                logger.warning(f"Could not enable intelligent tiering for {bucket_name}: {str(e)}")
            
            return {
                'resource_name': bucket_name,
                'optimization_type': 's3_lifecycle',
                'status': 'success',
                'estimated_savings': analysis['potential_savings'],
                'details': 'Lifecycle policy and intelligent tiering enabled'
            }
            
        except Exception as e:
            return {
                'resource_name': bucket_name,
                'optimization_type': 's3_lifecycle',
                'status': 'failed',
                'error': str(e),
                'estimated_savings': 0
            }

    def _implement_backup_lifecycle_optimization(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Implement AWS Backup lifecycle optimization"""
        backup_vault = analysis['resource_name']
        
        try:
            # Update backup plan with lifecycle rules
            # This would require updating the backup plan configuration
            # For now, we'll return a placeholder implementation
            
            return {
                'resource_name': backup_vault,
                'optimization_type': 'backup_lifecycle',
                'status': 'planned',
                'estimated_savings': analysis['potential_savings'],
                'details': 'Backup lifecycle optimization requires manual backup plan update'
            }
            
        except Exception as e:
            return {
                'resource_name': backup_vault,
                'optimization_type': 'backup_lifecycle',
                'status': 'failed',
                'error': str(e),
                'estimated_savings': 0
            }

    def _implement_retention_optimization(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Implement retention policy optimization"""
        try:
            # Retention optimization would depend on the specific service
            # This is a placeholder for the implementation logic
            
            return {
                'resource_name': analysis['resource_name'],
                'optimization_type': 'retention_policies',
                'status': 'planned',
                'estimated_savings': analysis['potential_savings'] * 0.3,  # Conservative estimate
                'details': 'Retention policy optimization requires policy review and approval'
            }
            
        except Exception as e:
            return {
                'resource_name': analysis['resource_name'],
                'optimization_type': 'retention_policies',
                'status': 'failed',
                'error': str(e),
                'estimated_savings': 0
            }

    def setup_cost_monitoring(self) -> Dict[str, Any]:
        """Setup automated cost monitoring and alerts"""
        logger.info("Setting up cost monitoring and alerts")
        
        monitoring_config = {
            'timestamp': datetime.utcnow().isoformat(),
            'cloudwatch_alarms': [],
            'sns_topics': [],
            'budgets': [],
            'status': 'success'
        }
        
        try:
            # 1. Create CloudWatch alarms for backup costs
            alarm_configs = [
                {
                    'name': f'{self.config.project_name}-backup-cost-high',
                    'description': 'Alert when backup costs exceed threshold',
                    'threshold': self.config.notification_threshold,
                    'comparison': 'GreaterThanThreshold'
                },
                {
                    'name': f'{self.config.project_name}-backup-cost-anomaly',
                    'description': 'Alert on backup cost anomalies',
                    'threshold': self.config.notification_threshold * 1.5,
                    'comparison': 'GreaterThanThreshold'
                }
            ]
            
            for alarm_config in alarm_configs:
                alarm_name = alarm_config['name']
                
                # Note: Cost metrics would typically come from Cost Explorer
                # This is a simplified implementation
                try:
                    self.cloudwatch.put_metric_alarm(
                        AlarmName=alarm_name,
                        ComparisonOperator=alarm_config['comparison'],
                        EvaluationPeriods=1,
                        MetricName='BackupCost',
                        Namespace=f'{self.config.project_name}/Backup',
                        Period=86400,  # Daily
                        Statistic='Sum',
                        Threshold=alarm_config['threshold'],
                        ActionsEnabled=True,
                        AlarmDescription=alarm_config['description'],
                        Unit='None'
                    )
                    
                    monitoring_config['cloudwatch_alarms'].append({
                        'name': alarm_name,
                        'status': 'created',
                        'threshold': alarm_config['threshold']
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to create alarm {alarm_name}: {str(e)}")
                    monitoring_config['cloudwatch_alarms'].append({
                        'name': alarm_name,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # 2. Setup cost budget (using AWS Budgets API would be implemented here)
            budget_config = {
                'budget_name': f'{self.config.project_name}-backup-budget',
                'budget_limit': self.config.notification_threshold * 12,  # Annual budget
                'alert_threshold': 80  # Alert at 80% of budget
            }
            
            monitoring_config['budgets'].append({
                'name': budget_config['budget_name'],
                'status': 'planned',
                'details': 'Budget creation requires AWS Budgets API implementation'
            })
            
        except Exception as e:
            logger.error(f"Error setting up cost monitoring: {str(e)}")
            monitoring_config['status'] = 'failed'
            monitoring_config['error'] = str(e)
        
        return monitoring_config

    def generate_cost_forecast(self, analysis_result: Dict[str, Any], 
                             forecast_months: int = 12) -> Dict[str, Any]:
        """Generate cost forecast based on current trends"""
        logger.info(f"Generating {forecast_months}-month cost forecast")
        
        current_monthly_cost = analysis_result['total_current_cost']
        optimized_monthly_cost = analysis_result['total_optimized_cost']
        
        # Calculate growth factors
        growth_factor = 1.05  # Assume 5% monthly growth
        optimization_implementation_rate = 0.8  # 80% of optimizations will be implemented
        
        forecast = {
            'forecast_period_months': forecast_months,
            'current_trajectory': [],
            'optimized_trajectory': [],
            'cumulative_savings': [],
            'total_projected_savings': 0.0,
            'roi_analysis': {}
        }
        
        cumulative_savings = 0.0
        
        for month in range(1, forecast_months + 1):
            # Current cost trajectory (with growth)
            current_cost = current_monthly_cost * (growth_factor ** month)
            
            # Optimized cost trajectory
            optimized_cost = optimized_monthly_cost * (growth_factor ** month)
            
            # Apply optimization implementation gradually
            implementation_factor = min(1.0, month * 0.1)  # 10% implementation per month
            actual_optimized_cost = current_cost - (
                (current_cost - optimized_cost) * optimization_implementation_rate * implementation_factor
            )
            
            monthly_savings = current_cost - actual_optimized_cost
            cumulative_savings += monthly_savings
            
            forecast['current_trajectory'].append({
                'month': month,
                'cost': current_cost
            })
            
            forecast['optimized_trajectory'].append({
                'month': month,
                'cost': actual_optimized_cost
            })
            
            forecast['cumulative_savings'].append({
                'month': month,
                'monthly_savings': monthly_savings,
                'cumulative_savings': cumulative_savings
            })
        
        forecast['total_projected_savings'] = cumulative_savings
        
        # ROI analysis
        implementation_cost = 5000  # Estimated implementation cost
        forecast['roi_analysis'] = {
            'implementation_cost': implementation_cost,
            'payback_period_months': implementation_cost / (current_monthly_cost - optimized_monthly_cost) if (current_monthly_cost - optimized_monthly_cost) > 0 else float('inf'),
            'roi_percentage': (cumulative_savings - implementation_cost) / implementation_cost * 100 if implementation_cost > 0 else 0
        }
        
        return forecast

    def export_cost_report(self, analysis_result: Dict[str, Any], 
                          forecast: Dict[str, Any] = None, 
                          format: str = 'json') -> str:
        """Export comprehensive cost analysis report"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'report_metadata': {
                'generated': datetime.utcnow().isoformat(),
                'project': self.config.project_name,
                'environment': self.config.environment,
                'report_version': '1.0'
            },
            'cost_analysis': analysis_result,
            'forecast': forecast,
            'executive_summary': self._generate_executive_summary(analysis_result, forecast)
        }
        
        if format.lower() == 'json':
            filename = f"backup_cost_analysis_{self.config.environment}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
                
        elif format.lower() == 'csv':
            filename = f"backup_cost_analysis_{self.config.environment}_{timestamp}.csv"
            # Convert analysis to DataFrame
            df_data = []
            for analysis in analysis_result['detailed_analysis']:
                df_data.append({
                    'Resource Type': analysis['resource_type'],
                    'Resource Name': analysis['resource_name'],
                    'Current Monthly Cost': analysis['current_monthly_cost'],
                    'Optimized Monthly Cost': analysis['optimized_monthly_cost'],
                    'Potential Savings': analysis['potential_savings'],
                    'Savings Percentage': analysis['savings_percentage']
                })
            
            df = pd.DataFrame(df_data)
            df.to_csv(filename, index=False)
            
        elif format.lower() == 'html':
            filename = f"backup_cost_analysis_{self.config.environment}_{timestamp}.html"
            self._generate_html_report(report, filename)
        
        logger.info(f"Cost analysis report exported to: {filename}")
        return filename

    def _generate_executive_summary(self, analysis_result: Dict[str, Any], 
                                  forecast: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate executive summary of cost analysis"""
        summary = {
            'current_monthly_cost': analysis_result['total_current_cost'],
            'potential_monthly_savings': analysis_result['total_potential_savings'],
            'savings_percentage': (analysis_result['total_potential_savings'] / analysis_result['total_current_cost'] * 100) if analysis_result['total_current_cost'] > 0 else 0,
            'top_cost_drivers': [],
            'high_impact_optimizations': [],
            'implementation_priority': 'High' if analysis_result['total_potential_savings'] > 100 else 'Medium'
        }
        
        # Identify top cost drivers
        analyses = analysis_result['detailed_analysis']
        sorted_analyses = sorted(analyses, key=lambda x: x['current_monthly_cost'], reverse=True)
        
        summary['top_cost_drivers'] = [
            {
                'resource': analysis['resource_name'],
                'type': analysis['resource_type'],
                'monthly_cost': analysis['current_monthly_cost']
            }
            for analysis in sorted_analyses[:3]
        ]
        
        # High-impact optimizations
        high_impact = sorted(analyses, key=lambda x: x['potential_savings'], reverse=True)
        summary['high_impact_optimizations'] = [
            {
                'resource': analysis['resource_name'],
                'optimization': analysis['optimization_recommendations'][0] if analysis['optimization_recommendations'] else 'General optimization',
                'potential_savings': analysis['potential_savings']
            }
            for analysis in high_impact[:3]
        ]
        
        if forecast:
            summary['annual_projected_savings'] = forecast['total_projected_savings']
            summary['roi_analysis'] = forecast['roi_analysis']
        
        return summary

    def _generate_html_report(self, report: Dict[str, Any], filename: str):
        """Generate HTML cost analysis report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backup Cost Analysis - {self.config.project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 10px; }}
        .summary {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }}
        .metric-card {{ background-color: #e8f5e8; padding: 15px; border-radius: 8px; min-width: 200px; }}
        .cost-breakdown {{ margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .savings {{ color: green; font-weight: bold; }}
        .cost {{ color: #333; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Backup Cost Analysis Report</h1>
        <p><strong>Project:</strong> {report['report_metadata']['project']}</p>
        <p><strong>Environment:</strong> {report['report_metadata']['environment']}</p>
        <p><strong>Generated:</strong> {report['report_metadata']['generated']}</p>
    </div>
    
    <div class="summary">
        <div class="metric-card">
            <h3>Current Monthly Cost</h3>
            <p class="cost" style="font-size: 24px;">${report['cost_analysis']['total_current_cost']:.2f}</p>
        </div>
        <div class="metric-card">
            <h3>Potential Monthly Savings</h3>
            <p class="savings" style="font-size: 24px;">${report['cost_analysis']['total_potential_savings']:.2f}</p>
        </div>
        <div class="metric-card">
            <h3>Savings Percentage</h3>
            <p class="savings" style="font-size: 24px;">{report['executive_summary']['savings_percentage']:.1f}%</p>
        </div>
    </div>
    
    <div class="cost-breakdown">
        <h2>Cost Breakdown by Resource</h2>
        <table>
            <tr>
                <th>Resource Type</th>
                <th>Resource Name</th>
                <th>Current Monthly Cost</th>
                <th>Optimized Cost</th>
                <th>Potential Savings</th>
                <th>Savings %</th>
            </tr>
"""
        
        for analysis in report['cost_analysis']['detailed_analysis']:
            html_content += f"""
            <tr>
                <td>{analysis['resource_type']}</td>
                <td>{analysis['resource_name']}</td>
                <td class="cost">${analysis['current_monthly_cost']:.2f}</td>
                <td class="cost">${analysis['optimized_monthly_cost']:.2f}</td>
                <td class="savings">${analysis['potential_savings']:.2f}</td>
                <td class="savings">{analysis['savings_percentage']:.1f}%</td>
            </tr>
"""
        
        html_content += """
        </table>
    </div>
    
    <div class="recommendations">
        <h2>Optimization Recommendations</h2>
        <ul>
"""
        
        for rec in report['cost_analysis']['optimization_recommendations']:
            html_content += f"<li>{rec}</li>"
        
        html_content += """
        </ul>
    </div>
</body>
</html>
        """
        
        with open(filename, 'w') as f:
            f.write(html_content)


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='AI Nutritionist Backup Cost Optimization')
    parser.add_argument('--environment', '-e', default='prod', help='Environment')
    parser.add_argument('--project-name', '-p', default='ai-nutritionist', help='Project name')
    parser.add_argument('--analysis-period', type=int, default=30, help='Analysis period in days')
    parser.add_argument('--target-savings', type=float, default=20.0, help='Target savings percentage')
    parser.add_argument('--implement-optimizations', action='store_true', help='Implement optimizations')
    parser.add_argument('--setup-monitoring', action='store_true', help='Setup cost monitoring')
    parser.add_argument('--generate-forecast', action='store_true', help='Generate cost forecast')
    parser.add_argument('--forecast-months', type=int, default=12, help='Forecast period in months')
    parser.add_argument('--export-format', choices=['json', 'csv', 'html'], default='json', help='Report format')
    
    args = parser.parse_args()
    
    # Create configuration
    config = CostOptimizationConfig(
        project_name=args.project_name,
        environment=args.environment,
        analysis_period_days=args.analysis_period,
        target_savings_percentage=args.target_savings
    )
    
    # Create cost optimizer
    optimizer = BackupCostOptimizer(config)
    
    # Run cost analysis
    print(f"Analyzing backup costs for {args.project_name} ({args.environment})")
    analysis_result = optimizer.analyze_backup_costs()
    
    # Generate forecast if requested
    forecast = None
    if args.generate_forecast:
        print("Generating cost forecast...")
        forecast = optimizer.generate_cost_forecast(analysis_result, args.forecast_months)
    
    # Implement optimizations if requested
    if args.implement_optimizations:
        print("Implementing cost optimizations...")
        implementation_result = optimizer.implement_cost_optimizations(analysis_result)
        print(f"Estimated monthly savings from implemented optimizations: ${implementation_result['estimated_monthly_savings']:.2f}")
    
    # Setup monitoring if requested
    if args.setup_monitoring:
        print("Setting up cost monitoring...")
        monitoring_result = optimizer.setup_cost_monitoring()
        print(f"Cost monitoring setup: {monitoring_result['status']}")
    
    # Export report
    report_file = optimizer.export_cost_report(analysis_result, forecast, args.export_format)
    
    # Print summary
    print("\n" + "="*80)
    print("BACKUP COST OPTIMIZATION SUMMARY")
    print("="*80)
    print(f"Current Monthly Cost: ${analysis_result['total_current_cost']:.2f}")
    print(f"Optimized Monthly Cost: ${analysis_result['total_optimized_cost']:.2f}")
    print(f"Potential Monthly Savings: ${analysis_result['total_potential_savings']:.2f}")
    print(f"Savings Percentage: {(analysis_result['total_potential_savings']/analysis_result['total_current_cost']*100):.1f}%")
    print(f"Report exported to: {report_file}")
    
    if forecast:
        print(f"Annual Projected Savings: ${forecast['total_projected_savings']:.2f}")
        print(f"ROI: {forecast['roi_analysis']['roi_percentage']:.1f}%")


if __name__ == "__main__":
    main()
