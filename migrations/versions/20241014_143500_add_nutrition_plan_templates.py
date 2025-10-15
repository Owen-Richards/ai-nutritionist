"""
Add Nutrition Plan Templates Table

Revision ID: 20241014_143500
Previous: 20241014_143000
Created: 2024-10-14T14:35:00Z

This migration creates the nutrition plan templates table
for storing pre-configured meal plans and nutritional templates.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def upgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    """
    Apply the migration - Create nutrition plan templates table.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    """
    logger.info("Creating nutrition plan templates table...")
    
    table_name = f"{config.dynamodb_table_prefix}-nutrition-templates"
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'template_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'template_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'template_category',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'created_date',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'dietary_restrictions',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'category-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'template_category',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'created_date',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'dietary-restrictions-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'dietary_restrictions',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'created_date',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'INCLUDE',
                        'NonKeyAttributes': [
                            'template_id',
                            'template_name',
                            'description',
                            'calories_per_day',
                            'is_active'
                        ]
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            },
            Tags=[
                {
                    'Key': 'Purpose',
                    'Value': 'NutritionTemplates'
                },
                {
                    'Key': 'Migration',
                    'Value': '20241014_143500'
                },
                {
                    'Key': 'Environment',
                    'Value': config.aws_region
                }
            ]
        )
        
        # Wait for table to be active
        logger.info("Waiting for nutrition templates table to become active...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 60
            }
        )
        
        # Seed with initial template data
        _seed_template_data(table, config, result)
        
        logger.info(f"✅ Created nutrition templates table: {table_name}")
        result.affected_tables.append(table_name)
        
        # Record metrics
        result.metrics['tables_created'] = 1
        result.metrics['indexes_created'] = 2
        result.metrics['templates_seeded'] = 3
        
    except Exception as e:
        logger.error(f"❌ Failed to create nutrition templates table: {e}")
        raise


def _seed_template_data(table, config, result):
    """Seed the table with initial template data."""
    logger.info("Seeding nutrition templates with initial data...")
    
    templates = [
        {
            'template_id': 'weight-loss-standard',
            'template_name': 'Standard Weight Loss Plan',
            'template_category': 'weight-loss',
            'dietary_restrictions': 'none',
            'description': 'Balanced calorie-deficit plan for sustainable weight loss',
            'calories_per_day': 1500,
            'macros': {
                'protein': 30,  # percentage
                'carbs': 40,
                'fat': 30
            },
            'meal_count': 3,
            'snack_count': 2,
            'is_active': True,
            'created_date': datetime.now(timezone.utc).isoformat(),
            'created_by': 'system',
            'version': '1.0'
        },
        {
            'template_id': 'muscle-gain-standard',
            'template_name': 'Standard Muscle Gain Plan',
            'template_category': 'muscle-gain',
            'dietary_restrictions': 'none',
            'description': 'High-protein plan optimized for muscle building',
            'calories_per_day': 2200,
            'macros': {
                'protein': 35,
                'carbs': 40,
                'fat': 25
            },
            'meal_count': 4,
            'snack_count': 2,
            'is_active': True,
            'created_date': datetime.now(timezone.utc).isoformat(),
            'created_by': 'system',
            'version': '1.0'
        },
        {
            'template_id': 'maintenance-vegetarian',
            'template_name': 'Vegetarian Maintenance Plan',
            'template_category': 'maintenance',
            'dietary_restrictions': 'vegetarian',
            'description': 'Balanced vegetarian plan for weight maintenance',
            'calories_per_day': 1800,
            'macros': {
                'protein': 25,
                'carbs': 50,
                'fat': 25
            },
            'meal_count': 3,
            'snack_count': 1,
            'is_active': True,
            'created_date': datetime.now(timezone.utc).isoformat(),
            'created_by': 'system',
            'version': '1.0'
        }
    ]
    
    for template in templates:
        table.put_item(Item=template)
    
    logger.info(f"✅ Seeded {len(templates)} nutrition templates")


def downgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    """
    Rollback the migration - Delete nutrition templates table.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    """
    logger.info("Rolling back nutrition templates table creation...")
    
    table_name = f"{config.dynamodb_table_prefix}-nutrition-templates"
    
    try:
        # Check if table exists
        try:
            dynamodb_client.describe_table(TableName=table_name)
        except dynamodb_client.exceptions.ResourceNotFoundException:
            logger.info(f"Table {table_name} does not exist, nothing to rollback")
            return
        
        # Delete the table
        table = dynamodb.Table(table_name)
        table.delete()
        
        # Wait for table to be deleted
        logger.info("Waiting for nutrition templates table deletion...")
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 60
            }
        )
        
        logger.info(f"✅ Deleted nutrition templates table: {table_name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to delete nutrition templates table: {e}")
        raise
