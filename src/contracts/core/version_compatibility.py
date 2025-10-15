"""
Version Compatibility Checker - Detects breaking changes between contract versions.

Analyzes contract changes to determine if they introduce breaking changes
and provides compatibility assessments.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from ..exceptions import VersionCompatibilityError


logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes in contracts."""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    DEPRECATED = "deprecated"


class CompatibilityLevel(Enum):
    """Levels of compatibility."""
    FULLY_COMPATIBLE = "fully_compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    INCOMPATIBLE = "incompatible"


class VersionCompatibilityChecker:
    """Checks version compatibility and detects breaking changes."""
    
    def __init__(self):
        """Initialize version compatibility checker."""
        self._breaking_change_rules = {
            "rest": self._check_rest_breaking_changes,
            "graphql": self._check_graphql_breaking_changes,
            "grpc": self._check_grpc_breaking_changes,
            "event": self._check_event_breaking_changes
        }
    
    def check_breaking_changes(
        self,
        old_interactions: List[Dict],
        new_interactions: List[Dict],
        contract_type: str
    ) -> Dict[str, Any]:
        """
        Check for breaking changes between contract versions.
        
        Args:
            old_interactions: Previous version interactions
            new_interactions: New version interactions
            contract_type: Type of contract
            
        Returns:
            Breaking changes analysis
        """
        if contract_type not in self._breaking_change_rules:
            raise VersionCompatibilityError(f"Unsupported contract type: {contract_type}")
        
        checker_func = self._breaking_change_rules[contract_type]
        return checker_func(old_interactions, new_interactions)
    
    def assess_compatibility(
        self,
        old_version: str,
        new_version: str,
        changes: List[Dict]
    ) -> Dict[str, Any]:
        """
        Assess compatibility level between versions.
        
        Args:
            old_version: Previous version
            new_version: New version
            changes: List of detected changes
            
        Returns:
            Compatibility assessment
        """
        has_breaking = any(change["type"] == ChangeType.BREAKING.value for change in changes)
        has_deprecated = any(change["type"] == ChangeType.DEPRECATED.value for change in changes)
        
        if has_breaking:
            compatibility_level = CompatibilityLevel.INCOMPATIBLE
        elif has_deprecated:
            compatibility_level = CompatibilityLevel.BACKWARD_COMPATIBLE
        else:
            compatibility_level = CompatibilityLevel.FULLY_COMPATIBLE
        
        return {
            "old_version": old_version,
            "new_version": new_version,
            "compatibility_level": compatibility_level.value,
            "has_breaking_changes": has_breaking,
            "has_deprecated_changes": has_deprecated,
            "total_changes": len(changes),
            "breaking_changes": [c for c in changes if c["type"] == ChangeType.BREAKING.value],
            "non_breaking_changes": [c for c in changes if c["type"] == ChangeType.NON_BREAKING.value],
            "deprecated_changes": [c for c in changes if c["type"] == ChangeType.DEPRECATED.value],
            "assessed_at": datetime.utcnow().isoformat()
        }
    
    def generate_migration_guide(
        self,
        old_interactions: List[Dict],
        new_interactions: List[Dict],
        contract_type: str
    ) -> Dict[str, Any]:
        """
        Generate migration guide for version upgrade.
        
        Args:
            old_interactions: Previous version interactions
            new_interactions: New version interactions
            contract_type: Type of contract
            
        Returns:
            Migration guide
        """
        changes_analysis = self.check_breaking_changes(
            old_interactions, new_interactions, contract_type
        )
        
        migration_steps = []
        warnings = []
        
        for change in changes_analysis["changes"]:
            if change["type"] == ChangeType.BREAKING.value:
                migration_steps.append({
                    "step": f"Update {change['location']}: {change['description']}",
                    "action_required": True,
                    "details": change.get("details", "")
                })
            elif change["type"] == ChangeType.DEPRECATED.value:
                warnings.append({
                    "warning": f"Deprecated {change['location']}: {change['description']}",
                    "timeline": change.get("removal_timeline", "Future version"),
                    "replacement": change.get("replacement", "TBD")
                })
        
        return {
            "migration_required": changes_analysis["has_breaking_changes"],
            "steps": migration_steps,
            "warnings": warnings,
            "compatibility_level": self.assess_compatibility(
                "old", "new", changes_analysis["changes"]
            )["compatibility_level"],
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _check_rest_breaking_changes(
        self,
        old_interactions: List[Dict],
        new_interactions: List[Dict]
    ) -> Dict[str, Any]:
        """Check breaking changes in REST API contracts."""
        changes = []
        
        # Create lookup maps
        old_map = {self._get_rest_interaction_key(i): i for i in old_interactions}
        new_map = {self._get_rest_interaction_key(i): i for i in new_interactions}
        
        # Check for removed interactions
        for key, old_interaction in old_map.items():
            if key not in new_map:
                changes.append({
                    "type": ChangeType.BREAKING.value,
                    "category": "removed_endpoint",
                    "location": f"{old_interaction['request']['method']} {old_interaction['request']['path']}",
                    "description": "Endpoint removed",
                    "impact": "High - clients will receive 404 errors"
                })
        
        # Check for modified interactions
        for key, new_interaction in new_map.items():
            if key in old_map:
                old_interaction = old_map[key]
                interaction_changes = self._compare_rest_interactions(old_interaction, new_interaction)
                changes.extend(interaction_changes)
        
        # Check for new interactions (non-breaking)
        for key, new_interaction in new_map.items():
            if key not in old_map:
                changes.append({
                    "type": ChangeType.NON_BREAKING.value,
                    "category": "new_endpoint",
                    "location": f"{new_interaction['request']['method']} {new_interaction['request']['path']}",
                    "description": "New endpoint added",
                    "impact": "None - backward compatible"
                })
        
        return {
            "has_breaking_changes": any(c["type"] == ChangeType.BREAKING.value for c in changes),
            "changes": changes,
            "total_changes": len(changes),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _compare_rest_interactions(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare two REST interactions for changes."""
        changes = []
        
        # Compare request changes
        old_req = old["request"]
        new_req = new["request"]
        
        # Check for added required parameters
        old_params = set(old_req.get("query_params", {}).keys())
        new_params = set(new_req.get("query_params", {}).keys())
        
        for param in new_params - old_params:
            # Assume new parameters are required (breaking) unless explicitly optional
            changes.append({
                "type": ChangeType.BREAKING.value,
                "category": "new_required_parameter",
                "location": f"{new_req['method']} {new_req['path']}",
                "description": f"New required parameter: {param}",
                "impact": "Medium - existing requests may fail validation"
            })
        
        # Check for removed parameters (potentially breaking)
        for param in old_params - new_params:
            changes.append({
                "type": ChangeType.BREAKING.value,
                "category": "removed_parameter",
                "location": f"{new_req['method']} {new_req['path']}",
                "description": f"Parameter removed: {param}",
                "impact": "Low - parameter will be ignored"
            })
        
        # Compare response changes
        old_resp = old["response"]
        new_resp = new["response"]
        
        # Check status code changes
        if old_resp["status"] != new_resp["status"]:
            changes.append({
                "type": ChangeType.BREAKING.value,
                "category": "status_code_change",
                "location": f"{new_req['method']} {new_req['path']}",
                "description": f"Status code changed from {old_resp['status']} to {new_resp['status']}",
                "impact": "High - client error handling may break"
            })
        
        # Check response schema changes if available
        if "schema" in old_resp and "schema" in new_resp:
            schema_changes = self._compare_json_schemas(
                old_resp["schema"], new_resp["schema"], 
                f"{new_req['method']} {new_req['path']} response"
            )
            changes.extend(schema_changes)
        
        return changes
    
    def _compare_json_schemas(self, old_schema: Dict, new_schema: Dict, location: str) -> List[Dict]:
        """Compare JSON schemas for breaking changes."""
        changes = []
        
        # Check for removed required fields
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        
        for field in old_required - new_required:
            changes.append({
                "type": ChangeType.NON_BREAKING.value,
                "category": "field_optional",
                "location": location,
                "description": f"Field '{field}' is no longer required",
                "impact": "None - backward compatible"
            })
        
        for field in new_required - old_required:
            changes.append({
                "type": ChangeType.BREAKING.value,
                "category": "new_required_field",
                "location": location,
                "description": f"Field '{field}' is now required",
                "impact": "High - responses may be missing required field"
            })
        
        # Check for removed fields
        old_props = set(old_schema.get("properties", {}).keys())
        new_props = set(new_schema.get("properties", {}).keys())
        
        for field in old_props - new_props:
            changes.append({
                "type": ChangeType.BREAKING.value,
                "category": "removed_field",
                "location": location,
                "description": f"Field '{field}' removed",
                "impact": "Medium - clients expecting this field will break"
            })
        
        for field in new_props - old_props:
            changes.append({
                "type": ChangeType.NON_BREAKING.value,
                "category": "new_field",
                "location": location,
                "description": f"Field '{field}' added",
                "impact": "None - backward compatible"
            })
        
        # Check for type changes in existing fields
        old_props_dict = old_schema.get("properties", {})
        new_props_dict = new_schema.get("properties", {})
        
        for field in old_props & new_props:
            old_type = old_props_dict[field].get("type")
            new_type = new_props_dict[field].get("type")
            
            if old_type and new_type and old_type != new_type:
                changes.append({
                    "type": ChangeType.BREAKING.value,
                    "category": "type_change",
                    "location": f"{location}.{field}",
                    "description": f"Type changed from {old_type} to {new_type}",
                    "impact": "High - type deserialization will fail"
                })
        
        return changes
    
    def _check_graphql_breaking_changes(
        self,
        old_interactions: List[Dict],
        new_interactions: List[Dict]
    ) -> Dict[str, Any]:
        """Check breaking changes in GraphQL contracts."""
        changes = []
        
        # GraphQL breaking changes analysis
        # This is a simplified implementation
        
        old_queries = {i.get("description", i.get("query", "")): i for i in old_interactions}
        new_queries = {i.get("description", i.get("query", "")): i for i in new_interactions}
        
        # Check for removed queries
        for desc, old_query in old_queries.items():
            if desc not in new_queries:
                changes.append({
                    "type": ChangeType.BREAKING.value,
                    "category": "removed_query",
                    "location": desc,
                    "description": "GraphQL query/mutation removed",
                    "impact": "High - clients using this query will fail"
                })
        
        return {
            "has_breaking_changes": any(c["type"] == ChangeType.BREAKING.value for c in changes),
            "changes": changes,
            "total_changes": len(changes),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _check_grpc_breaking_changes(
        self,
        old_interactions: List[Dict],
        new_interactions: List[Dict]
    ) -> Dict[str, Any]:
        """Check breaking changes in gRPC contracts."""
        changes = []
        
        # gRPC breaking changes analysis
        # This is a placeholder implementation
        
        return {
            "has_breaking_changes": False,
            "changes": changes,
            "total_changes": len(changes),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _check_event_breaking_changes(
        self,
        old_interactions: List[Dict],
        new_interactions: List[Dict]
    ) -> Dict[str, Any]:
        """Check breaking changes in event-driven contracts."""
        changes = []
        
        # Event schema breaking changes analysis
        old_events = {i.get("event_type", ""): i for i in old_interactions}
        new_events = {i.get("event_type", ""): i for i in new_interactions}
        
        # Check for removed event types
        for event_type, old_event in old_events.items():
            if event_type not in new_events:
                changes.append({
                    "type": ChangeType.BREAKING.value,
                    "category": "removed_event_type",
                    "location": event_type,
                    "description": f"Event type '{event_type}' removed",
                    "impact": "High - consumers expecting this event will break"
                })
        
        # Check for schema changes in existing events
        for event_type, new_event in new_events.items():
            if event_type in old_events:
                old_event = old_events[event_type]
                if "schema" in old_event and "schema" in new_event:
                    schema_changes = self._compare_json_schemas(
                        old_event["schema"], new_event["schema"],
                        f"Event {event_type}"
                    )
                    changes.extend(schema_changes)
        
        return {
            "has_breaking_changes": any(c["type"] == ChangeType.BREAKING.value for c in changes),
            "changes": changes,
            "total_changes": len(changes),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _get_rest_interaction_key(self, interaction: Dict) -> str:
        """Get unique key for REST interaction."""
        request = interaction["request"]
        return f"{request['method']}:{request['path']}"
