"""
Data Consistency Validation

Cross-service consistency, event sourcing validation,
cache consistency, and database consistency checks.
"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
from collections import defaultdict

from .validators import ValidationResult

logger = logging.getLogger(__name__)


class ConsistencyLevel(Enum):
    """Levels of consistency checking."""
    EVENTUAL = "eventual"
    STRONG = "strong"
    WEAK = "weak"


@dataclass
class ConsistencyCheck:
    """Configuration for a consistency check."""
    name: str
    source_service: str
    target_service: str
    key_field: str
    comparison_fields: List[str]
    consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL
    tolerance_seconds: int = 300  # 5 minutes default
    critical: bool = False


@dataclass
class ConsistencyViolation:
    """Represents a consistency violation."""
    check_name: str
    entity_id: str
    source_value: Any
    target_value: Any
    field_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: str = "medium"


class CrossServiceConsistencyValidator:
    """Validates consistency across microservices."""
    
    def __init__(self):
        self.checks = {}
        self.service_adapters = {}
        self.violation_handlers = []
    
    def register_consistency_check(self, check: ConsistencyCheck):
        """Register a consistency check between services."""
        self.checks[check.name] = check
    
    def register_service_adapter(self, service_name: str, adapter: Callable):
        """Register an adapter to fetch data from a service."""
        self.service_adapters[service_name] = adapter
    
    def add_violation_handler(self, handler: Callable[[ConsistencyViolation], None]):
        """Add a handler for consistency violations."""
        self.violation_handlers.append(handler)
    
    async def validate_cross_service_consistency(self, check_name: str, 
                                               entity_ids: List[str]) -> ValidationResult:
        """Validate consistency for specific entities across services."""
        result = ValidationResult(is_valid=True)
        
        if check_name not in self.checks:
            result.add_error(f"Unknown consistency check: {check_name}")
            return result
        
        check = self.checks[check_name]
        violations = []
        
        try:
            # Fetch data from both services
            source_adapter = self.service_adapters.get(check.source_service)
            target_adapter = self.service_adapters.get(check.target_service)
            
            if not source_adapter or not target_adapter:
                result.add_error(f"Missing service adapters for {check.source_service} or {check.target_service}")
                return result
            
            for entity_id in entity_ids:
                source_data = await source_adapter(entity_id)
                target_data = await target_adapter(entity_id)
                
                if not source_data or not target_data:
                    if check.critical:
                        result.add_error(f"Missing data for entity {entity_id}")
                    else:
                        result.add_warning(f"Missing data for entity {entity_id}")
                    continue
                
                # Compare specified fields
                for field in check.comparison_fields:
                    source_value = self._get_nested_value(source_data, field)
                    target_value = self._get_nested_value(target_data, field)
                    
                    if not self._values_consistent(source_value, target_value, check):
                        violation = ConsistencyViolation(
                            check_name=check_name,
                            entity_id=entity_id,
                            source_value=source_value,
                            target_value=target_value,
                            field_name=field,
                            severity="high" if check.critical else "medium"
                        )
                        violations.append(violation)
                        
                        if check.critical:
                            result.add_error(f"Critical consistency violation: {field} mismatch for {entity_id}")
                        else:
                            result.add_warning(f"Consistency violation: {field} mismatch for {entity_id}")
            
            # Handle violations
            for violation in violations:
                for handler in self.violation_handlers:
                    try:
                        handler(violation)
                    except Exception as e:
                        logger.error(f"Error in violation handler: {e}")
        
        except Exception as e:
            result.add_error(f"Error during consistency validation: {str(e)}")
        
        result.metadata['violations'] = violations
        return result
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _values_consistent(self, source_value: Any, target_value: Any, 
                          check: ConsistencyCheck) -> bool:
        """Check if two values are consistent based on the check configuration."""
        if source_value == target_value:
            return True
        
        # Handle different consistency levels
        if check.consistency_level == ConsistencyLevel.WEAK:
            # Allow more tolerance for eventual consistency
            if isinstance(source_value, (int, float)) and isinstance(target_value, (int, float)):
                return abs(source_value - target_value) < 0.1
        
        elif check.consistency_level == ConsistencyLevel.EVENTUAL:
            # Check timestamps if available
            if isinstance(source_value, dict) and isinstance(target_value, dict):
                source_ts = source_value.get('updated_at') or source_value.get('timestamp')
                target_ts = target_value.get('updated_at') or target_value.get('timestamp')
                
                if source_ts and target_ts:
                    try:
                        source_time = datetime.fromisoformat(source_ts.replace('Z', '+00:00'))
                        target_time = datetime.fromisoformat(target_ts.replace('Z', '+00:00'))
                        time_diff = abs((source_time - target_time).total_seconds())
                        
                        if time_diff <= check.tolerance_seconds:
                            return True
                    except Exception:
                        pass
        
        return False


class EventSourcingValidator:
    """Validates event sourcing integrity and consistency."""
    
    def __init__(self):
        self.event_store = None
        self.aggregate_validators = {}
        self.event_handlers = {}
    
    def set_event_store(self, event_store):
        """Set the event store for validation."""
        self.event_store = event_store
    
    def register_aggregate_validator(self, aggregate_type: str, validator: Callable):
        """Register a validator for an aggregate type."""
        self.aggregate_validators[aggregate_type] = validator
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for event validation."""
        self.event_handlers[event_type] = handler
    
    async def validate_event_sequence(self, aggregate_id: str, 
                                    aggregate_type: str) -> ValidationResult:
        """Validate the event sequence for an aggregate."""
        result = ValidationResult(is_valid=True)
        
        if not self.event_store:
            result.add_error("Event store not configured")
            return result
        
        try:
            events = await self.event_store.get_events(aggregate_id)
            
            # Validate event sequence order
            previous_sequence = -1
            for event in events:
                current_sequence = event.get('sequence_number', 0)
                if current_sequence != previous_sequence + 1:
                    result.add_error(f"Event sequence gap: expected {previous_sequence + 1}, got {current_sequence}")
                previous_sequence = current_sequence
            
            # Validate aggregate state reconstruction
            if aggregate_type in self.aggregate_validators:
                validator = self.aggregate_validators[aggregate_type]
                try:
                    reconstructed_state = await validator(events)
                    result.metadata['reconstructed_state'] = reconstructed_state
                except Exception as e:
                    result.add_error(f"Failed to reconstruct aggregate state: {str(e)}")
            
            # Validate individual events
            for event in events:
                event_type = event.get('event_type')
                if event_type in self.event_handlers:
                    handler = self.event_handlers[event_type]
                    try:
                        event_result = await handler(event)
                        if not event_result:
                            result.add_error(f"Event validation failed for {event_type}")
                    except Exception as e:
                        result.add_error(f"Error validating event {event_type}: {str(e)}")
        
        except Exception as e:
            result.add_error(f"Error during event sequence validation: {str(e)}")
        
        return result
    
    async def validate_event_causality(self, events: List[Dict[str, Any]]) -> ValidationResult:
        """Validate causal relationships between events."""
        result = ValidationResult(is_valid=True)
        
        event_map = {event['event_id']: event for event in events}
        
        for event in events:
            caused_by = event.get('caused_by')
            if caused_by:
                if caused_by not in event_map:
                    result.add_error(f"Event {event['event_id']} references non-existent causal event {caused_by}")
                else:
                    causal_event = event_map[caused_by]
                    if causal_event['timestamp'] > event['timestamp']:
                        result.add_error(f"Causal event {caused_by} has later timestamp than effect {event['event_id']}")
        
        return result


class CacheConsistencyValidator:
    """Validates cache consistency with source data."""
    
    def __init__(self):
        self.cache_adapters = {}
        self.source_adapters = {}
        self.consistency_rules = {}
    
    def register_cache_adapter(self, cache_name: str, adapter: Callable):
        """Register a cache adapter."""
        self.cache_adapters[cache_name] = adapter
    
    def register_source_adapter(self, source_name: str, adapter: Callable):
        """Register a source data adapter."""
        self.source_adapters[source_name] = adapter
    
    def register_consistency_rule(self, cache_name: str, source_name: str, 
                                 key_transformer: Optional[Callable] = None,
                                 value_transformer: Optional[Callable] = None):
        """Register a consistency rule between cache and source."""
        self.consistency_rules[cache_name] = {
            'source': source_name,
            'key_transformer': key_transformer,
            'value_transformer': value_transformer
        }
    
    async def validate_cache_consistency(self, cache_name: str, 
                                       keys: List[str]) -> ValidationResult:
        """Validate cache consistency for specified keys."""
        result = ValidationResult(is_valid=True)
        
        if cache_name not in self.consistency_rules:
            result.add_error(f"No consistency rule for cache: {cache_name}")
            return result
        
        rule = self.consistency_rules[cache_name]
        cache_adapter = self.cache_adapters.get(cache_name)
        source_adapter = self.source_adapters.get(rule['source'])
        
        if not cache_adapter or not source_adapter:
            result.add_error(f"Missing adapters for cache or source validation")
            return result
        
        try:
            inconsistencies = []
            
            for key in keys:
                # Transform key if needed
                source_key = key
                if rule['key_transformer']:
                    source_key = rule['key_transformer'](key)
                
                # Fetch from cache and source
                cache_value = await cache_adapter(key)
                source_value = await source_adapter(source_key)
                
                # Transform values if needed
                if rule['value_transformer']:
                    if cache_value:
                        cache_value = rule['value_transformer'](cache_value)
                    if source_value:
                        source_value = rule['value_transformer'](source_value)
                
                # Compare values
                if cache_value != source_value:
                    inconsistencies.append({
                        'key': key,
                        'cache_value': cache_value,
                        'source_value': source_value
                    })
                    result.add_warning(f"Cache inconsistency for key: {key}")
            
            result.metadata['inconsistencies'] = inconsistencies
            result.metadata['total_keys_checked'] = len(keys)
            result.metadata['inconsistent_keys'] = len(inconsistencies)
        
        except Exception as e:
            result.add_error(f"Error during cache consistency validation: {str(e)}")
        
        return result
    
    async def validate_cache_expiration(self, cache_name: str) -> ValidationResult:
        """Validate cache expiration policies."""
        result = ValidationResult(is_valid=True)
        
        if cache_name not in self.cache_adapters:
            result.add_error(f"No adapter for cache: {cache_name}")
            return result
        
        try:
            cache_adapter = self.cache_adapters[cache_name]
            
            # Get cache statistics (this depends on cache implementation)
            stats = await cache_adapter.get_stats() if hasattr(cache_adapter, 'get_stats') else {}
            
            if stats:
                expired_keys = stats.get('expired_keys', 0)
                total_keys = stats.get('total_keys', 0)
                
                if total_keys > 0:
                    expiration_rate = expired_keys / total_keys
                    if expiration_rate > 0.8:  # More than 80% expired
                        result.add_warning(f"High expiration rate ({expiration_rate:.2%}) in cache {cache_name}")
                
                result.metadata['cache_stats'] = stats
        
        except Exception as e:
            result.add_error(f"Error validating cache expiration: {str(e)}")
        
        return result


class DatabaseConsistencyValidator:
    """Validates database consistency and integrity."""
    
    def __init__(self):
        self.db_connections = {}
        self.consistency_checks = []
    
    def register_database(self, db_name: str, connection):
        """Register a database connection."""
        self.db_connections[db_name] = connection
    
    def add_consistency_check(self, check_name: str, query: str, 
                            expected_result: Any = None, 
                            validation_func: Optional[Callable] = None):
        """Add a database consistency check."""
        self.consistency_checks.append({
            'name': check_name,
            'query': query,
            'expected_result': expected_result,
            'validation_func': validation_func
        })
    
    async def validate_database_consistency(self, db_name: str) -> ValidationResult:
        """Run all consistency checks for a database."""
        result = ValidationResult(is_valid=True)
        
        if db_name not in self.db_connections:
            result.add_error(f"No connection for database: {db_name}")
            return result
        
        connection = self.db_connections[db_name]
        
        for check in self.consistency_checks:
            try:
                check_result = await self._run_consistency_check(connection, check)
                if not check_result['passed']:
                    result.add_error(f"Consistency check '{check['name']}' failed: {check_result['message']}")
                else:
                    result.add_warning(f"Consistency check '{check['name']}' passed")
            
            except Exception as e:
                result.add_error(f"Error running consistency check '{check['name']}': {str(e)}")
        
        return result
    
    async def _run_consistency_check(self, connection, check: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single consistency check."""
        try:
            # Execute query (this is a simplified example)
            if hasattr(connection, 'execute'):
                cursor = await connection.execute(check['query'])
                result_data = await cursor.fetchall()
            else:
                # Assume it's a different type of connection
                result_data = await connection.query(check['query'])
            
            # Validate result
            if check['validation_func']:
                passed = check['validation_func'](result_data)
                message = "Custom validation passed" if passed else "Custom validation failed"
            elif check['expected_result'] is not None:
                passed = result_data == check['expected_result']
                message = f"Expected {check['expected_result']}, got {result_data}"
            else:
                # For queries that should return no results (e.g., orphaned records)
                passed = len(result_data) == 0
                message = f"Found {len(result_data)} inconsistent records"
            
            return {
                'passed': passed,
                'message': message,
                'result_data': result_data
            }
        
        except Exception as e:
            return {
                'passed': False,
                'message': f"Query execution failed: {str(e)}",
                'result_data': None
            }
    
    async def validate_foreign_key_integrity(self, db_name: str, 
                                           table_relationships: Dict[str, List[Dict]]) -> ValidationResult:
        """Validate foreign key integrity across tables."""
        result = ValidationResult(is_valid=True)
        
        if db_name not in self.db_connections:
            result.add_error(f"No connection for database: {db_name}")
            return result
        
        connection = self.db_connections[db_name]
        
        for table, relationships in table_relationships.items():
            for rel in relationships:
                parent_table = rel['parent_table']
                foreign_key = rel['foreign_key']
                parent_key = rel.get('parent_key', 'id')
                
                # Query to find orphaned records
                query = f"""
                    SELECT COUNT(*) as orphaned_count
                    FROM {table} t1
                    LEFT JOIN {parent_table} t2 ON t1.{foreign_key} = t2.{parent_key}
                    WHERE t1.{foreign_key} IS NOT NULL AND t2.{parent_key} IS NULL
                """
                
                try:
                    check_result = await self._run_consistency_check(connection, {
                        'name': f"FK integrity: {table}.{foreign_key} -> {parent_table}.{parent_key}",
                        'query': query,
                        'expected_result': [(0,)]  # No orphaned records
                    })
                    
                    if not check_result['passed']:
                        result.add_error(f"Foreign key integrity violation: {check_result['message']}")
                
                except Exception as e:
                    result.add_error(f"Error checking FK integrity for {table}.{foreign_key}: {str(e)}")
        
        return result
