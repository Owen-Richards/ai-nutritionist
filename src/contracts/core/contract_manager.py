"""
Contract Manager - Central orchestrator for contract testing.

Manages the lifecycle of contracts, including creation, validation,
publishing, and version management.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from ..exceptions import ContractValidationError, VersionCompatibilityError
from .schema_validator import SchemaValidator
from .version_compatibility import VersionCompatibilityChecker


logger = logging.getLogger(__name__)


class ContractManager:
    """Central manager for contract testing operations."""
    
    def __init__(self, contract_dir: Union[str, Path] = None):
        """
        Initialize contract manager.
        
        Args:
            contract_dir: Directory to store contracts (defaults to ./contracts)
        """
        self.contract_dir = Path(contract_dir or "contracts")
        self.contract_dir.mkdir(exist_ok=True)
        
        self.schema_validator = SchemaValidator()
        self.version_checker = VersionCompatibilityChecker()
        
        # Contract registry
        self._contracts: Dict[str, Dict] = {}
        self._load_existing_contracts()
    
    def create_contract(
        self,
        consumer: str,
        provider: str,
        contract_type: str = "rest",
        interactions: List[Dict] = None,
        metadata: Dict = None
    ) -> str:
        """
        Create a new contract.
        
        Args:
            consumer: Consumer service name
            provider: Provider service name
            contract_type: Type of contract (rest, graphql, grpc, event)
            interactions: List of interaction definitions
            metadata: Additional contract metadata
            
        Returns:
            Contract ID
        """
        contract_id = str(uuid4())
        
        contract = {
            "id": contract_id,
            "consumer": consumer,
            "provider": provider,
            "contract_type": contract_type,
            "version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
            "interactions": interactions or [],
            "metadata": metadata or {}
        }
        
        # Validate contract structure
        self._validate_contract_structure(contract)
        
        # Store contract
        self._contracts[contract_id] = contract
        self._save_contract(contract)
        
        logger.info(f"Created contract {contract_id} between {consumer} and {provider}")
        return contract_id
    
    def validate_contract(self, contract_id: str) -> bool:
        """
        Validate a contract.
        
        Args:
            contract_id: Contract identifier
            
        Returns:
            True if valid
            
        Raises:
            ContractValidationError: If validation fails
        """
        if contract_id not in self._contracts:
            raise ContractValidationError(f"Contract {contract_id} not found")
        
        contract = self._contracts[contract_id]
        
        try:
            # Validate contract structure
            self._validate_contract_structure(contract)
            
            # Validate interactions based on contract type
            if contract["contract_type"] == "rest":
                self._validate_rest_interactions(contract["interactions"])
            elif contract["contract_type"] == "graphql":
                self._validate_graphql_interactions(contract["interactions"])
            elif contract["contract_type"] == "grpc":
                self._validate_grpc_interactions(contract["interactions"])
            elif contract["contract_type"] == "event":
                self._validate_event_interactions(contract["interactions"])
            
            logger.info(f"Contract {contract_id} validation successful")
            return True
            
        except Exception as e:
            raise ContractValidationError(
                f"Contract validation failed: {str(e)}",
                contract_type=contract["contract_type"],
                details={"contract_id": contract_id}
            )
    
    def publish_contract(self, contract_id: str, registry_url: str = None) -> bool:
        """
        Publish contract to registry.
        
        Args:
            contract_id: Contract identifier
            registry_url: Contract registry URL (optional)
            
        Returns:
            True if published successfully
        """
        if contract_id not in self._contracts:
            raise ContractValidationError(f"Contract {contract_id} not found")
        
        contract = self._contracts[contract_id]
        
        # First validate the contract
        self.validate_contract(contract_id)
        
        # Mark as published
        contract["published_at"] = datetime.utcnow().isoformat()
        contract["status"] = "published"
        
        # Save updated contract
        self._save_contract(contract)
        
        logger.info(f"Published contract {contract_id}")
        return True
    
    def check_breaking_changes(
        self,
        contract_id: str,
        new_interactions: List[Dict]
    ) -> Dict[str, Any]:
        """
        Check for breaking changes in contract update.
        
        Args:
            contract_id: Contract identifier
            new_interactions: New interaction definitions
            
        Returns:
            Breaking changes analysis
        """
        if contract_id not in self._contracts:
            raise ContractValidationError(f"Contract {contract_id} not found")
        
        current_contract = self._contracts[contract_id]
        current_interactions = current_contract["interactions"]
        
        return self.version_checker.check_breaking_changes(
            current_interactions,
            new_interactions,
            current_contract["contract_type"]
        )
    
    def update_contract(
        self,
        contract_id: str,
        new_interactions: List[Dict],
        version: str = None,
        force: bool = False
    ) -> str:
        """
        Update an existing contract.
        
        Args:
            contract_id: Contract identifier
            new_interactions: New interaction definitions
            version: New version (auto-increment if not provided)
            force: Force update even with breaking changes
            
        Returns:
            New contract ID
        """
        if contract_id not in self._contracts:
            raise ContractValidationError(f"Contract {contract_id} not found")
        
        current_contract = self._contracts[contract_id]
        
        # Check for breaking changes
        breaking_changes = self.check_breaking_changes(contract_id, new_interactions)
        
        if breaking_changes["has_breaking_changes"] and not force:
            raise VersionCompatibilityError(
                "Breaking changes detected. Use force=True to proceed.",
                version_from=current_contract["version"],
                version_to=version or "auto",
                breaking_changes=breaking_changes["changes"]
            )
        
        # Create new version
        new_version = version or self._increment_version(
            current_contract["version"],
            breaking_changes["has_breaking_changes"]
        )
        
        new_contract_id = str(uuid4())
        new_contract = current_contract.copy()
        new_contract.update({
            "id": new_contract_id,
            "version": new_version,
            "interactions": new_interactions,
            "updated_at": datetime.utcnow().isoformat(),
            "previous_version": contract_id
        })
        
        # Validate new contract
        self._validate_contract_structure(new_contract)
        
        # Store new contract
        self._contracts[new_contract_id] = new_contract
        self._save_contract(new_contract)
        
        logger.info(f"Updated contract {contract_id} to {new_contract_id} (v{new_version})")
        return new_contract_id
    
    def get_contract(self, contract_id: str) -> Optional[Dict]:
        """Get contract by ID."""
        return self._contracts.get(contract_id)
    
    def list_contracts(
        self,
        consumer: str = None,
        provider: str = None,
        contract_type: str = None
    ) -> List[Dict]:
        """
        List contracts with optional filtering.
        
        Args:
            consumer: Filter by consumer
            provider: Filter by provider
            contract_type: Filter by contract type
            
        Returns:
            List of matching contracts
        """
        contracts = list(self._contracts.values())
        
        if consumer:
            contracts = [c for c in contracts if c["consumer"] == consumer]
        if provider:
            contracts = [c for c in contracts if c["provider"] == provider]
        if contract_type:
            contracts = [c for c in contracts if c["contract_type"] == contract_type]
        
        return contracts
    
    def _validate_contract_structure(self, contract: Dict) -> None:
        """Validate basic contract structure."""
        required_fields = ["id", "consumer", "provider", "contract_type", "version", "interactions"]
        
        for field in required_fields:
            if field not in contract:
                raise ContractValidationError(f"Missing required field: {field}")
        
        if not isinstance(contract["interactions"], list):
            raise ContractValidationError("interactions must be a list")
    
    def _validate_rest_interactions(self, interactions: List[Dict]) -> None:
        """Validate REST API interactions."""
        for interaction in interactions:
            required_fields = ["description", "request", "response"]
            for field in required_fields:
                if field not in interaction:
                    raise ContractValidationError(f"REST interaction missing: {field}")
            
            # Validate request structure
            request = interaction["request"]
            if "method" not in request or "path" not in request:
                raise ContractValidationError("REST request must have method and path")
            
            # Validate response structure
            response = interaction["response"]
            if "status" not in response:
                raise ContractValidationError("REST response must have status")
    
    def _validate_graphql_interactions(self, interactions: List[Dict]) -> None:
        """Validate GraphQL interactions."""
        for interaction in interactions:
            if "query" not in interaction or "response" not in interaction:
                raise ContractValidationError("GraphQL interaction must have query and response")
    
    def _validate_grpc_interactions(self, interactions: List[Dict]) -> None:
        """Validate gRPC interactions."""
        for interaction in interactions:
            required_fields = ["service", "method", "request", "response"]
            for field in required_fields:
                if field not in interaction:
                    raise ContractValidationError(f"gRPC interaction missing: {field}")
    
    def _validate_event_interactions(self, interactions: List[Dict]) -> None:
        """Validate event-driven interactions."""
        for interaction in interactions:
            required_fields = ["event_type", "schema", "channel"]
            for field in required_fields:
                if field not in interaction:
                    raise ContractValidationError(f"Event interaction missing: {field}")
    
    def _load_existing_contracts(self) -> None:
        """Load existing contracts from disk."""
        for contract_file in self.contract_dir.glob("*.json"):
            try:
                with open(contract_file, 'r') as f:
                    contract = json.load(f)
                    self._contracts[contract["id"]] = contract
            except Exception as e:
                logger.warning(f"Failed to load contract {contract_file}: {e}")
    
    def _save_contract(self, contract: Dict) -> None:
        """Save contract to disk."""
        contract_file = self.contract_dir / f"{contract['id']}.json"
        with open(contract_file, 'w') as f:
            json.dump(contract, f, indent=2)
    
    def _increment_version(self, current_version: str, is_breaking: bool) -> str:
        """Increment version based on change type."""
        parts = current_version.split('.')
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if is_breaking:
            major += 1
            minor = 0
            patch = 0
        else:
            minor += 1
            patch = 0
        
        return f"{major}.{minor}.{patch}"
