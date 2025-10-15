"""
Initial User Analytics Table Creation

Revision ID: 20241014_143000
Created: 2024-10-14T14:30:00Z

This migration creates the user analytics table for tracking
user behavior and engagement metrics.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def upgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    """
    Apply the migration - Create user analytics table.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    """
    logger.info("Creating user analytics table...")
    
    table_name = f"{config.dynamodb_table_prefix}-user-analytics"
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'event_timestamp',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'event_timestamp',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'event_type',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'event_date',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'event-type-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'event_type',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'event_timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'daily-events-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'event_date',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'event_timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'KEYS_ONLY'
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            },
            Tags=[
                {
                    'Key': 'Purpose',
                    'Value': 'UserAnalytics'
                },
                {
                    'Key': 'Migration',
                    'Value': '20241014_143000'
                },
                {
                    'Key': 'Environment',
                    'Value': config.aws_region
                }
            ]
        )
        
        # Wait for table to be active
        logger.info("Waiting for table to become active...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 60  # 5 minutes max
            }
        )
        
        logger.info(f"✅ Created user analytics table: {table_name}")
        result.affected_tables.append(table_name)
        
        # Record metrics
        result.metrics['tables_created'] = 1
        result.metrics['indexes_created'] = 2
        result.metrics['streams_enabled'] = 1
        
    except Exception as e:
        logger.error(f"❌ Failed to create user analytics table: {e}")
        raise


def downgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    """
    Rollback the migration - Delete user analytics table.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    """
    logger.info("Rolling back user analytics table creation...")
    
    table_name = f"{config.dynamodb_table_prefix}-user-analytics"
    
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
        logger.info("Waiting for table deletion...")
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 60
            }
        )
        
        logger.info(f"✅ Deleted user analytics table: {table_name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to delete user analytics table: {e}")
        raise
