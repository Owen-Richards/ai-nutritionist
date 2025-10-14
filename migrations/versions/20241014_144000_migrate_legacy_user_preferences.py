"""
Data Migration: Migrate Legacy User Preferences

Revision ID: 20241014_144000
Previous: 20241014_143500
Created: 2024-10-14T14:40:00Z

This migration converts legacy user preference format to new schema
and migrates existing data to the updated structure.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def upgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    """
    Apply the migration - Transform legacy user preferences data.
    
    This is a data migration that:
    1. Scans existing user records
    2. Transforms legacy preference format
    3. Updates records with new schema
    4. Validates data integrity
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    """
    logger.info("Starting legacy user preferences migration...")
    
    user_table_name = f"{config.dynamodb_table_prefix}-users"
    
    try:
        # Get user table
        user_table = dynamodb.Table(user_table_name)
        
        # Scan for users with legacy preferences
        legacy_users = []
        paginator = dynamodb_client.get_paginator('scan')
        
        for page in paginator.paginate(
            TableName=user_table_name,
            FilterExpression='attribute_exists(legacy_preferences)'
        ):
            for item in page.get('Items', []):
                legacy_users.append(item)
        
        logger.info(f"Found {len(legacy_users)} users with legacy preferences")
        
        # Process users in batches
        batch_size = 25  # DynamoDB batch write limit
        processed_count = 0
        error_count = 0
        
        for i in range(0, len(legacy_users), batch_size):
            batch = legacy_users[i:i + batch_size]
            
            try:
                # Process batch
                batch_results = _process_user_batch(batch, user_table, config)
                processed_count += batch_results['processed']
                error_count += batch_results['errors']
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{processed_count} users migrated, {error_count} errors")
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                error_count += len(batch)
        
        # Validate migration results
        validation_results = _validate_migration(user_table, config)
        
        logger.info(f"✅ Migration completed: {processed_count} users migrated, "
                   f"{error_count} errors, {validation_results['valid']} validated")
        
        # Record metrics
        result.metrics['users_migrated'] = processed_count
        result.metrics['migration_errors'] = error_count
        result.metrics['validation_passed'] = validation_results['valid']
        result.metrics['validation_failed'] = validation_results['invalid']
        
        if error_count > 0:
            logger.warning(f"Migration completed with {error_count} errors")
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate user preferences: {e}")
        raise


def _process_user_batch(users: List[Dict], user_table, config) -> Dict[str, int]:
    """Process a batch of users for preference migration."""
    processed = 0
    errors = 0
    
    for user in users:
        try:
            # Extract legacy preferences
            legacy_prefs = user.get('legacy_preferences', {})
            if isinstance(legacy_prefs, str):
                legacy_prefs = json.loads(legacy_prefs)
            
            # Transform to new schema
            new_preferences = _transform_preferences(legacy_prefs)
            
            # Update user record
            user_table.update_item(
                Key={'user_id': user['user_id']},
                UpdateExpression="""
                    SET preferences = :new_prefs,
                        migration_metadata = :metadata
                    REMOVE legacy_preferences
                """,
                ExpressionAttributeValues={
                    ':new_prefs': new_preferences,
                    ':metadata': {
                        'migrated_at': datetime.now(timezone.utc).isoformat(),
                        'migration_version': '20241014_144000',
                        'legacy_backup': legacy_prefs
                    }
                }
            )
            
            processed += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate user {user.get('user_id', 'unknown')}: {e}")
            errors += 1
    
    return {'processed': processed, 'errors': errors}


def _transform_preferences(legacy_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Transform legacy preference format to new schema."""
    
    # Default new structure
    new_prefs = {
        'dietary': {
            'restrictions': [],
            'allergies': [],
            'preferred_cuisines': [],
            'disliked_foods': []
        },
        'nutrition_goals': {
            'primary_goal': 'maintenance',
            'target_calories': None,
            'macro_preferences': {
                'protein': 25,
                'carbs': 45,
                'fat': 30
            }
        },
        'meal_planning': {
            'meals_per_day': 3,
            'snacks_per_day': 1,
            'prep_time_limit': 30,
            'cooking_skill': 'intermediate'
        },
        'notifications': {
            'meal_reminders': True,
            'progress_updates': True,
            'educational_tips': True
        }
    }
    
    # Map legacy fields to new structure
    if 'diet_type' in legacy_prefs:
        diet_mapping = {
            'vegetarian': ['vegetarian'],
            'vegan': ['vegan'],
            'keto': ['ketogenic'],
            'paleo': ['paleo'],
            'low_carb': ['low-carb']
        }
        new_prefs['dietary']['restrictions'] = diet_mapping.get(
            legacy_prefs['diet_type'], []
        )
    
    if 'allergies' in legacy_prefs:
        # Legacy format was comma-separated string
        if isinstance(legacy_prefs['allergies'], str):
            new_prefs['dietary']['allergies'] = [
                allergy.strip() for allergy in legacy_prefs['allergies'].split(',')
                if allergy.strip()
            ]
        elif isinstance(legacy_prefs['allergies'], list):
            new_prefs['dietary']['allergies'] = legacy_prefs['allergies']
    
    if 'goal' in legacy_prefs:
        goal_mapping = {
            'lose_weight': 'weight-loss',
            'gain_weight': 'weight-gain',
            'maintain': 'maintenance',
            'build_muscle': 'muscle-gain'
        }
        new_prefs['nutrition_goals']['primary_goal'] = goal_mapping.get(
            legacy_prefs['goal'], 'maintenance'
        )
    
    if 'daily_calories' in legacy_prefs:
        new_prefs['nutrition_goals']['target_calories'] = legacy_prefs['daily_calories']
    
    if 'meal_count' in legacy_prefs:
        new_prefs['meal_planning']['meals_per_day'] = legacy_prefs['meal_count']
    
    # Handle notification preferences
    if 'notifications' in legacy_prefs:
        legacy_notifs = legacy_prefs['notifications']
        if isinstance(legacy_notifs, dict):
            new_prefs['notifications'].update(legacy_notifs)
        elif isinstance(legacy_notifs, bool):
            # Legacy boolean format - apply to all notifications
            new_prefs['notifications'] = {
                'meal_reminders': legacy_notifs,
                'progress_updates': legacy_notifs,
                'educational_tips': legacy_notifs
            }
    
    return new_prefs


def _validate_migration(user_table, config) -> Dict[str, int]:
    """Validate the migration results."""
    logger.info("Validating migration results...")
    
    valid_count = 0
    invalid_count = 0
    
    # Sample validation - check 100 migrated users
    response = user_table.scan(
        FilterExpression='attribute_exists(migration_metadata)',
        Limit=100
    )
    
    for item in response.get('Items', []):
        try:
            # Validate new preference structure
            prefs = item.get('preferences', {})
            
            # Check required sections exist
            required_sections = ['dietary', 'nutrition_goals', 'meal_planning', 'notifications']
            if all(section in prefs for section in required_sections):
                valid_count += 1
            else:
                invalid_count += 1
                
        except Exception:
            invalid_count += 1
    
    return {'valid': valid_count, 'invalid': invalid_count}


def downgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    """
    Rollback the migration - Restore legacy preferences format.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    """
    logger.info("Rolling back user preferences migration...")
    
    user_table_name = f"{config.dynamodb_table_prefix}-users"
    
    try:
        user_table = dynamodb.Table(user_table_name)
        
        # Find users with migration metadata
        migrated_users = []
        paginator = dynamodb_client.get_paginator('scan')
        
        for page in paginator.paginate(
            TableName=user_table_name,
            FilterExpression='attribute_exists(migration_metadata)'
        ):
            for item in page.get('Items', []):
                migrated_users.append(item)
        
        logger.info(f"Found {len(migrated_users)} migrated users to rollback")
        
        # Process rollback in batches
        processed_count = 0
        error_count = 0
        batch_size = 25
        
        for i in range(0, len(migrated_users), batch_size):
            batch = migrated_users[i:i + batch_size]
            
            for user in batch:
                try:
                    # Restore legacy preferences from backup
                    migration_meta = user.get('migration_metadata', {})
                    legacy_backup = migration_meta.get('legacy_backup', {})
                    
                    if legacy_backup:
                        user_table.update_item(
                            Key={'user_id': user['user_id']},
                            UpdateExpression="""
                                SET legacy_preferences = :legacy_prefs
                                REMOVE preferences, migration_metadata
                            """,
                            ExpressionAttributeValues={
                                ':legacy_prefs': legacy_backup
                            }
                        )
                        processed_count += 1
                    else:
                        logger.warning(f"No legacy backup found for user {user['user_id']}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to rollback user {user.get('user_id', 'unknown')}: {e}")
                    error_count += 1
        
        logger.info(f"✅ Rollback completed: {processed_count} users restored, {error_count} errors")
        
    except Exception as e:
        logger.error(f"❌ Failed to rollback user preferences migration: {e}")
        raise
