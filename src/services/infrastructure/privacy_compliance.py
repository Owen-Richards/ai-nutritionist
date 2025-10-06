"""
G4 - Privacy & Data Compliance
DSAR export/delete, regional data routing, data retention, and GDPR compliance.
"""

import json
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
import asyncio
import threading
from collections import defaultdict

# Try importing optional dependencies
try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False


class DataRegion(str, Enum):
    """Supported data regions for compliance."""
    US_EAST = "us-east-1"
    EU_WEST = "eu-west-1"
    EU_CENTRAL = "eu-central-1"
    ASIA_PACIFIC = "ap-southeast-1"
    CANADA = "ca-central-1"


class DataCategory(str, Enum):
    """Categories of personal data."""
    IDENTITY = "identity"  # Name, email, phone
    PROFILE = "profile"    # Preferences, settings
    BEHAVIORAL = "behavioral"  # Usage patterns, analytics
    HEALTH = "health"      # Nutrition data, health metrics
    FINANCIAL = "financial"  # Payment information
    LOCATION = "location"   # Geographic data
    BIOMETRIC = "biometric"  # Biometric identifiers


class ConsentType(str, Enum):
    """Types of data processing consent."""
    ESSENTIAL = "essential"      # Required for service
    ANALYTICS = "analytics"      # Usage analytics
    MARKETING = "marketing"      # Marketing communications
    PERSONALIZATION = "personalization"  # Customized experience
    RESEARCH = "research"        # Product research


class RetentionPolicy(str, Enum):
    """Data retention policies."""
    IMMEDIATE = "immediate"      # Delete immediately
    SHORT_TERM = "short_term"    # 30 days
    MEDIUM_TERM = "medium_term"  # 1 year
    LONG_TERM = "long_term"      # 7 years
    PERMANENT = "permanent"      # Keep indefinitely


class DSARType(str, Enum):
    """Data Subject Access Request types."""
    ACCESS = "access"        # Right to access
    RECTIFICATION = "rectification"  # Right to rectify
    ERASURE = "erasure"      # Right to be forgotten
    PORTABILITY = "portability"  # Data portability
    RESTRICTION = "restriction"  # Restrict processing
    OBJECTION = "objection"   # Object to processing


@dataclass
class ConsentRecord:
    """User consent record."""
    user_id: str
    consent_type: ConsentType
    granted: bool
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    consent_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class DataInventoryItem:
    """Item in personal data inventory."""
    user_id: str
    data_category: DataCategory
    data_source: str  # e.g., "user_profiles", "meal_logs"
    data_description: str
    created_at: datetime
    last_updated: datetime
    retention_policy: RetentionPolicy
    region: DataRegion
    sensitive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        return data


@dataclass
class DSARRequest:
    """Data Subject Access Request."""
    request_id: str
    user_id: str
    request_type: DSARType
    requested_at: datetime
    status: str  # pending, processing, completed, failed
    completed_at: Optional[datetime] = None
    data_export_path: Optional[str] = None
    requester_email: str = ""
    verification_token: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['requested_at'] = self.requested_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


@dataclass
class RetentionRule:
    """Data retention rule."""
    name: str
    data_category: DataCategory
    retention_period: RetentionPolicy
    days: int  # Actual retention days
    conditions: Optional[Dict[str, Any]] = None  # Special conditions
    auto_delete: bool = True


class ConsentManager:
    """Manages user consent for different data processing activities."""
    
    def __init__(self):
        self.consent_records: Dict[str, List[ConsentRecord]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ConsentRecord:
        """Record user consent."""
        with self._lock:
            record = ConsentRecord(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.consent_records[user_id].append(record)
            return record
    
    def get_current_consent(self, user_id: str, consent_type: ConsentType) -> Optional[bool]:
        """Get current consent status for user and type."""
        with self._lock:
            user_consents = self.consent_records.get(user_id, [])
            
            # Find the most recent consent for this type
            for record in reversed(user_consents):
                if record.consent_type == consent_type:
                    return record.granted
            
            return None
    
    def get_all_consents(self, user_id: str) -> Dict[ConsentType, bool]:
        """Get all current consents for user."""
        consents = {}
        for consent_type in ConsentType:
            consents[consent_type] = self.get_current_consent(user_id, consent_type)
        return consents
    
    def withdraw_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Withdraw consent for specific type."""
        return self.record_consent(user_id, consent_type, False) is not None
    
    def get_consent_history(self, user_id: str) -> List[ConsentRecord]:
        """Get complete consent history for user."""
        with self._lock:
            return list(self.consent_records.get(user_id, []))


class DataInventoryManager:
    """Manages inventory of personal data across the system."""
    
    def __init__(self):
        self.inventory: Dict[str, List[DataInventoryItem]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def register_data(
        self,
        user_id: str,
        data_category: DataCategory,
        data_source: str,
        data_description: str,
        retention_policy: RetentionPolicy = RetentionPolicy.MEDIUM_TERM,
        region: DataRegion = DataRegion.US_EAST,
        sensitive: bool = False
    ) -> DataInventoryItem:
        """Register personal data in inventory."""
        with self._lock:
            item = DataInventoryItem(
                user_id=user_id,
                data_category=data_category,
                data_source=data_source,
                data_description=data_description,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                retention_policy=retention_policy,
                region=region,
                sensitive=sensitive
            )
            
            self.inventory[user_id].append(item)
            return item
    
    def get_user_data_inventory(self, user_id: str) -> List[DataInventoryItem]:
        """Get all data inventory items for user."""
        with self._lock:
            return list(self.inventory.get(user_id, []))
    
    def get_data_by_category(self, user_id: str, category: DataCategory) -> List[DataInventoryItem]:
        """Get user data by category."""
        with self._lock:
            return [
                item for item in self.inventory.get(user_id, [])
                if item.data_category == category
            ]
    
    def update_data_location(self, user_id: str, data_source: str, new_region: DataRegion):
        """Update data location for compliance."""
        with self._lock:
            for item in self.inventory.get(user_id, []):
                if item.data_source == data_source:
                    item.region = new_region
                    item.last_updated = datetime.utcnow()


class RetentionManager:
    """Manages data retention policies and automatic deletion."""
    
    def __init__(self):
        self.rules: List[RetentionRule] = []
        self.deletion_queue: List[Dict[str, Any]] = []
        self._setup_default_rules()
        self._start_retention_scheduler()
    
    def _setup_default_rules(self):
        """Setup default retention rules."""
        # Identity data - long term for legal compliance
        self.add_rule(RetentionRule(
            name="identity_data",
            data_category=DataCategory.IDENTITY,
            retention_period=RetentionPolicy.LONG_TERM,
            days=2555  # 7 years
        ))
        
        # Behavioral data - medium term
        self.add_rule(RetentionRule(
            name="behavioral_data",
            data_category=DataCategory.BEHAVIORAL,
            retention_period=RetentionPolicy.MEDIUM_TERM,
            days=365  # 1 year
        ))
        
        # Profile preferences - medium term
        self.add_rule(RetentionRule(
            name="profile_data",
            data_category=DataCategory.PROFILE,
            retention_period=RetentionPolicy.MEDIUM_TERM,
            days=365
        ))
        
        # Health data - long term with user consent
        self.add_rule(RetentionRule(
            name="health_data",
            data_category=DataCategory.HEALTH,
            retention_period=RetentionPolicy.LONG_TERM,
            days=2555,
            conditions={"requires_consent": True}
        ))
        
        # Financial data - long term for legal compliance
        self.add_rule(RetentionRule(
            name="financial_data",
            data_category=DataCategory.FINANCIAL,
            retention_period=RetentionPolicy.LONG_TERM,
            days=2555
        ))
    
    def add_rule(self, rule: RetentionRule):
        """Add retention rule."""
        self.rules.append(rule)
    
    def get_retention_period(self, data_category: DataCategory) -> int:
        """Get retention period in days for data category."""
        for rule in self.rules:
            if rule.data_category == data_category:
                return rule.days
        return 365  # Default 1 year
    
    def schedule_deletion(self, user_id: str, data_source: str, deletion_date: datetime):
        """Schedule data for deletion."""
        self.deletion_queue.append({
            'user_id': user_id,
            'data_source': data_source,
            'deletion_date': deletion_date,
            'scheduled_at': datetime.utcnow()
        })
    
    def _start_retention_scheduler(self):
        """Start background retention scheduler."""
        def retention_worker():
            while True:
                try:
                    self._process_retention_policies()
                    self._process_deletion_queue()
                except Exception as e:
                    print(f"Retention scheduler error: {e}")
                
                # Run daily
                import time
                time.sleep(86400)
        
        thread = threading.Thread(target=retention_worker, daemon=True)
        thread.start()
    
    def _process_retention_policies(self):
        """Process retention policies and mark data for deletion."""
        # This would integrate with actual data stores
        # For now, just a placeholder implementation
        pass
    
    def _process_deletion_queue(self):
        """Process scheduled deletions."""
        current_time = datetime.utcnow()
        
        # Process due deletions
        due_deletions = [
            item for item in self.deletion_queue
            if item['deletion_date'] <= current_time
        ]
        
        for deletion in due_deletions:
            try:
                # Perform actual deletion (would integrate with data stores)
                print(f"Deleting data: {deletion['user_id']} - {deletion['data_source']}")
                self.deletion_queue.remove(deletion)
            except Exception as e:
                print(f"Deletion failed: {e}")


class DSARProcessor:
    """Processes Data Subject Access Requests."""
    
    def __init__(
        self,
        consent_manager: ConsentManager,
        inventory_manager: DataInventoryManager,
        retention_manager: RetentionManager
    ):
        self.consent_manager = consent_manager
        self.inventory_manager = inventory_manager
        self.retention_manager = retention_manager
        self.requests: Dict[str, DSARRequest] = {}
        self._lock = threading.Lock()
    
    def submit_request(
        self,
        user_id: str,
        request_type: DSARType,
        requester_email: str = ""
    ) -> DSARRequest:
        """Submit a DSAR request."""
        with self._lock:
            request_id = str(uuid.uuid4())
            
            request = DSARRequest(
                request_id=request_id,
                user_id=user_id,
                request_type=request_type,
                requested_at=datetime.utcnow(),
                status="pending",
                requester_email=requester_email,
                verification_token=str(uuid.uuid4())
            )
            
            self.requests[request_id] = request
            
            # Start processing in background
            threading.Thread(
                target=self._process_request,
                args=(request_id,),
                daemon=True
            ).start()
            
            return request
    
    def get_request_status(self, request_id: str) -> Optional[DSARRequest]:
        """Get status of DSAR request."""
        with self._lock:
            return self.requests.get(request_id)
    
    def _process_request(self, request_id: str):
        """Process DSAR request in background."""
        try:
            with self._lock:
                request = self.requests.get(request_id)
                if not request:
                    return
                
                request.status = "processing"
            
            if request.request_type == DSARType.ACCESS:
                self._process_access_request(request)
            elif request.request_type == DSARType.ERASURE:
                self._process_erasure_request(request)
            elif request.request_type == DSARType.PORTABILITY:
                self._process_portability_request(request)
            elif request.request_type == DSARType.RECTIFICATION:
                self._process_rectification_request(request)
            
            with self._lock:
                request.status = "completed"
                request.completed_at = datetime.utcnow()
                
        except Exception as e:
            with self._lock:
                request.status = "failed"
                print(f"DSAR processing failed: {e}")
    
    def _process_access_request(self, request: DSARRequest):
        """Process data access request."""
        user_data = self._collect_user_data(request.user_id)
        
        # Create data export
        export_path = self._create_data_export(request.user_id, user_data)
        request.data_export_path = export_path
    
    def _process_erasure_request(self, request: DSARRequest):
        """Process data erasure request (right to be forgotten)."""
        # Get all user data
        inventory_items = self.inventory_manager.get_user_data_inventory(request.user_id)
        
        # Schedule deletion for each data source
        for item in inventory_items:
            # Immediate deletion for most data
            if item.data_category != DataCategory.FINANCIAL:  # Keep financial for legal compliance
                self.retention_manager.schedule_deletion(
                    request.user_id,
                    item.data_source,
                    datetime.utcnow()
                )
    
    def _process_portability_request(self, request: DSARRequest):
        """Process data portability request."""
        user_data = self._collect_user_data(request.user_id)
        
        # Create portable data export (structured format)
        export_path = self._create_portable_export(request.user_id, user_data)
        request.data_export_path = export_path
    
    def _process_rectification_request(self, request: DSARRequest):
        """Process data rectification request."""
        # This would require additional parameters for what to rectify
        # Placeholder implementation
        pass
    
    def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        """Collect all user data from various sources."""
        data = {
            "user_id": user_id,
            "collected_at": datetime.utcnow().isoformat(),
            "data_inventory": [],
            "consent_history": [],
            "profile_data": {},
            "behavioral_data": {},
            "health_data": {},
            "financial_data": {}
        }
        
        # Get data inventory
        inventory_items = self.inventory_manager.get_user_data_inventory(user_id)
        data["data_inventory"] = [item.to_dict() for item in inventory_items]
        
        # Get consent history
        consent_history = self.consent_manager.get_consent_history(user_id)
        data["consent_history"] = [record.to_dict() for record in consent_history]
        
        # Collect actual data from various sources
        # This would integrate with your actual data stores
        # For demo purposes, showing structure
        
        return data
    
    def _create_data_export(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create ZIP export of user data."""
        export_dir = Path(f"exports/{user_id}")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Create JSON files for different data categories
        for category, data in user_data.items():
            if data and category != "user_id" and category != "collected_at":
                file_path = export_dir / f"{category}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
        
        # Create ZIP archive
        zip_path = export_dir.parent / f"{user_id}_data_export.zip"
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for file_path in export_dir.glob("*.json"):
                zip_file.write(file_path, file_path.name)
        
        # Clean up individual files
        for file_path in export_dir.glob("*.json"):
            file_path.unlink()
        export_dir.rmdir()
        
        return str(zip_path)
    
    def _create_portable_export(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create portable data export in standard format."""
        # Similar to data export but in more standardized format
        return self._create_data_export(user_id, user_data)


class RegionalDataRouter:
    """Routes data to appropriate regions based on user location and regulations."""
    
    def __init__(self):
        self.region_mappings = {
            # European countries -> EU region
            'DE': DataRegion.EU_CENTRAL,
            'FR': DataRegion.EU_WEST,
            'IT': DataRegion.EU_WEST,
            'ES': DataRegion.EU_WEST,
            'NL': DataRegion.EU_WEST,
            'GB': DataRegion.EU_WEST,  # Post-Brexit but still GDPR compliant
            
            # North American countries -> US region
            'US': DataRegion.US_EAST,
            'CA': DataRegion.CANADA,
            
            # Asia Pacific
            'JP': DataRegion.ASIA_PACIFIC,
            'AU': DataRegion.ASIA_PACIFIC,
            'SG': DataRegion.ASIA_PACIFIC,
        }
    
    def get_region_for_country(self, country_code: str) -> DataRegion:
        """Get appropriate data region for country."""
        return self.region_mappings.get(country_code, DataRegion.US_EAST)
    
    def is_gdpr_region(self, region: DataRegion) -> bool:
        """Check if region requires GDPR compliance."""
        return region in [DataRegion.EU_WEST, DataRegion.EU_CENTRAL]
    
    def get_data_residency_requirements(self, country_code: str) -> Dict[str, Any]:
        """Get data residency requirements for country."""
        region = self.get_region_for_country(country_code)
        
        requirements = {
            "region": region,
            "gdpr_required": self.is_gdpr_region(region),
            "data_localization": country_code in ['DE', 'FR', 'RU', 'CN'],
            "special_categories_restricted": self.is_gdpr_region(region),
            "consent_required": True,
            "right_to_erasure": self.is_gdpr_region(region) or country_code == 'CA'
        }
        
        return requirements


class PrivacyComplianceService:
    """
    Comprehensive privacy and data compliance service.
    Handles GDPR, CCPA, and other privacy regulations.
    """
    
    def __init__(self, default_region: DataRegion = DataRegion.US_EAST):
        self.default_region = default_region
        
        # Initialize components
        self.consent_manager = ConsentManager()
        self.inventory_manager = DataInventoryManager()
        self.retention_manager = RetentionManager()
        self.dsar_processor = DSARProcessor(
            self.consent_manager,
            self.inventory_manager,
            self.retention_manager
        )
        self.regional_router = RegionalDataRouter()
    
    # Consent Management
    def record_user_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
        ip_address: Optional[str] = None
    ) -> bool:
        """Record user consent."""
        try:
            self.consent_manager.record_consent(
                user_id, consent_type, granted, ip_address
            )
            return True
        except Exception:
            return False
    
    def check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Check if user has granted consent for specific processing."""
        consent = self.consent_manager.get_current_consent(user_id, consent_type)
        return consent is True
    
    def withdraw_all_consent(self, user_id: str) -> bool:
        """Withdraw all consent for user."""
        try:
            for consent_type in ConsentType:
                self.consent_manager.withdraw_consent(user_id, consent_type)
            return True
        except Exception:
            return False
    
    # Data Inventory Management
    def register_personal_data(
        self,
        user_id: str,
        data_category: DataCategory,
        data_source: str,
        description: str,
        region: Optional[DataRegion] = None
    ) -> bool:
        """Register personal data in inventory."""
        try:
            self.inventory_manager.register_data(
                user_id=user_id,
                data_category=data_category,
                data_source=data_source,
                data_description=description,
                region=region or self.default_region
            )
            return True
        except Exception:
            return False
    
    # DSAR Processing
    def submit_data_request(
        self,
        user_id: str,
        request_type: DSARType,
        requester_email: str = ""
    ) -> str:
        """Submit Data Subject Access Request."""
        request = self.dsar_processor.submit_request(
            user_id, request_type, requester_email
        )
        return request.request_id
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get DSAR request status."""
        request = self.dsar_processor.get_request_status(request_id)
        return request.to_dict() if request else None
    
    # Regional Compliance
    def get_compliance_requirements(self, country_code: str) -> Dict[str, Any]:
        """Get compliance requirements for country."""
        return self.regional_router.get_data_residency_requirements(country_code)
    
    def validate_data_processing(
        self,
        user_id: str,
        processing_purpose: ConsentType,
        user_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate if data processing is compliant."""
        # Check consent
        has_consent = self.check_consent(user_id, processing_purpose)
        
        # Check regional requirements
        requirements = {}
        if user_country:
            requirements = self.get_compliance_requirements(user_country)
        
        return {
            "user_id": user_id,
            "processing_purpose": processing_purpose,
            "has_consent": has_consent,
            "compliant": has_consent,
            "requirements": requirements,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    # Data Lifecycle Management
    def schedule_data_deletion(self, user_id: str, reason: str = "user_request"):
        """Schedule user data for deletion."""
        # Get all user data
        inventory_items = self.inventory_manager.get_user_data_inventory(user_id)
        
        # Schedule deletion based on retention policies
        for item in inventory_items:
            if item.data_category != DataCategory.FINANCIAL:  # Legal requirement to keep
                deletion_date = datetime.utcnow() + timedelta(days=7)  # Grace period
                self.retention_manager.schedule_deletion(
                    user_id, item.data_source, deletion_date
                )
    
    def get_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's data and privacy status."""
        inventory_items = self.inventory_manager.get_user_data_inventory(user_id)
        consents = self.consent_manager.get_all_consents(user_id)
        
        return {
            "user_id": user_id,
            "data_categories": list(set(item.data_category for item in inventory_items)),
            "data_sources": list(set(item.data_source for item in inventory_items)),
            "total_data_items": len(inventory_items),
            "consents": {ct.value: granted for ct, granted in consents.items()},
            "regions": list(set(item.region for item in inventory_items)),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for privacy compliance service."""
        return {
            "status": "healthy",
            "total_users_tracked": len(self.consent_manager.consent_records),
            "total_data_items": sum(len(items) for items in self.inventory_manager.inventory.values()),
            "retention_rules": len(self.retention_manager.rules),
            "pending_dsars": len([r for r in self.dsar_processor.requests.values() if r.status == "pending"]),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global instance
privacy_service = PrivacyComplianceService()

# Convenience functions
def record_consent(user_id: str, consent_type: ConsentType, granted: bool) -> bool:
    """Global function to record consent."""
    return privacy_service.record_user_consent(user_id, consent_type, granted)

def check_processing_consent(user_id: str, purpose: ConsentType) -> bool:
    """Global function to check processing consent."""
    return privacy_service.check_consent(user_id, purpose)

def request_data_deletion(user_id: str) -> str:
    """Global function to request data deletion."""
    return privacy_service.submit_data_request(user_id, DSARType.ERASURE)
