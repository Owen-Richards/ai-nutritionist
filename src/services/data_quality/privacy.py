"""
Data Privacy Validation

PII detection, data masking verification, encryption validation,
and retention policy testing.
"""

import re
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple, Pattern
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from .validators import ValidationResult
from src.models.analytics import PIILevel, ConsentType
from src.services.infrastructure.privacy_compliance import DataCategory, RetentionPolicy

logger = logging.getLogger(__name__)


class PIIType(Enum):
    """Types of Personally Identifiable Information."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    IP_ADDRESS = "ip_address"
    DEVICE_ID = "device_id"
    BIOMETRIC = "biometric"
    HEALTH_DATA = "health_data"
    FINANCIAL = "financial"


@dataclass
class PIIPattern:
    """Pattern for detecting PII."""
    pii_type: PIIType
    pattern: Pattern[str]
    confidence: float  # 0.0 to 1.0
    description: str


@dataclass
class PIIDetection:
    """Result of PII detection."""
    pii_type: PIIType
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    field_path: str = ""


class PIIDetector:
    """Detects Personally Identifiable Information in data."""
    
    def __init__(self):
        self.patterns = []
        self.custom_patterns = {}
        self.whitelist_patterns = []
        self._initialize_default_patterns()
    
    def _initialize_default_patterns(self):
        """Initialize default PII detection patterns."""
        self.patterns = [
            # Email addresses
            PIIPattern(
                PIIType.EMAIL,
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                0.95,
                "Email address pattern"
            ),
            
            # Phone numbers (US format)
            PIIPattern(
                PIIType.PHONE,
                re.compile(r'\b(?:\+1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
                0.90,
                "US phone number pattern"
            ),
            
            # Social Security Numbers
            PIIPattern(
                PIIType.SSN,
                re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                0.98,
                "US Social Security Number"
            ),
            
            # Credit card numbers (basic pattern)
            PIIPattern(
                PIIType.CREDIT_CARD,
                re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
                0.85,
                "Credit card number pattern"
            ),
            
            # IP addresses
            PIIPattern(
                PIIType.IP_ADDRESS,
                re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
                0.95,
                "IPv4 address pattern"
            ),
            
            # Names (basic pattern - high false positives)
            PIIPattern(
                PIIType.NAME,
                re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),
                0.60,
                "Full name pattern (basic)"
            ),
            
            # Dates that might be DOB
            PIIPattern(
                PIIType.DATE_OF_BIRTH,
                re.compile(r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b'),
                0.70,
                "Date of birth pattern (MM/DD/YYYY or MM-DD-YYYY)"
            ),
        ]
    
    def add_custom_pattern(self, name: str, pattern: PIIPattern):
        """Add a custom PII detection pattern."""
        self.custom_patterns[name] = pattern
    
    def add_whitelist_pattern(self, pattern: Pattern[str], description: str = ""):
        """Add a pattern to whitelist (ignore during detection)."""
        self.whitelist_patterns.append({
            'pattern': pattern,
            'description': description
        })
    
    def detect_pii_in_text(self, text: str, field_path: str = "") -> List[PIIDetection]:
        """Detect PII in a text string."""
        detections = []
        
        if not isinstance(text, str):
            return detections
        
        # Check whitelist first
        for whitelist in self.whitelist_patterns:
            if whitelist['pattern'].search(text):
                logger.debug(f"Text whitelisted: {whitelist['description']}")
                return detections
        
        # Check all patterns
        all_patterns = list(self.patterns) + list(self.custom_patterns.values())
        
        for pattern in all_patterns:
            matches = pattern.pattern.finditer(text)
            for match in matches:
                detection = PIIDetection(
                    pii_type=pattern.pii_type,
                    value=match.group(),
                    confidence=pattern.confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    field_path=field_path
                )
                detections.append(detection)
        
        return detections
    
    def detect_pii_in_data(self, data: Any, path: str = "") -> List[PIIDetection]:
        """Recursively detect PII in structured data."""
        detections = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                detections.extend(self.detect_pii_in_data(value, current_path))
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                detections.extend(self.detect_pii_in_data(item, current_path))
        
        elif isinstance(data, str):
            detections.extend(self.detect_pii_in_text(data, path))
        
        return detections
    
    def validate_pii_classification(self, data: Dict[str, Any], 
                                  expected_pii_level: PIILevel) -> ValidationResult:
        """Validate that data is correctly classified for PII level."""
        result = ValidationResult(is_valid=True)
        
        detections = self.detect_pii_in_data(data)
        
        if expected_pii_level == PIILevel.NONE:
            if detections:
                high_confidence_detections = [d for d in detections if d.confidence > 0.8]
                if high_confidence_detections:
                    result.add_error(f"PII detected in data marked as PII-free: {[d.pii_type.value for d in high_confidence_detections]}")
                else:
                    result.add_warning(f"Possible PII detected in data marked as PII-free: {[d.pii_type.value for d in detections]}")
        
        elif expected_pii_level == PIILevel.PSEUDONYMIZED:
            # Should not contain direct identifiers
            direct_identifiers = [PIIType.EMAIL, PIIType.PHONE, PIIType.SSN, PIIType.NAME]
            direct_pii = [d for d in detections if d.pii_type in direct_identifiers and d.confidence > 0.8]
            if direct_pii:
                result.add_error(f"Direct PII found in pseudonymized data: {[d.pii_type.value for d in direct_pii]}")
        
        elif expected_pii_level == PIILevel.SENSITIVE:
            # This level allows PII, so just validate it's properly handled
            if not detections:
                result.add_warning("No PII detected in data marked as sensitive")
        
        result.metadata['detections'] = [
            {
                'type': d.pii_type.value,
                'confidence': d.confidence,
                'field_path': d.field_path,
                'value_preview': d.value[:10] + "..." if len(d.value) > 10 else d.value
            }
            for d in detections
        ]
        
        return result


class DataMaskingValidator:
    """Validates data masking and anonymization."""
    
    def __init__(self):
        self.masking_rules = {}
        self.reversibility_checks = {}
    
    def register_masking_rule(self, field_name: str, masking_type: str, 
                            validation_func: Optional[callable] = None):
        """Register a data masking rule."""
        self.masking_rules[field_name] = {
            'type': masking_type,
            'validator': validation_func
        }
    
    def validate_field_masking(self, field_name: str, original_value: Any, 
                             masked_value: Any) -> ValidationResult:
        """Validate that a field is properly masked."""
        result = ValidationResult(is_valid=True)
        
        if field_name not in self.masking_rules:
            result.add_warning(f"No masking rule defined for field: {field_name}")
            return result
        
        rule = self.masking_rules[field_name]
        masking_type = rule['type']
        
        try:
            if masking_type == "hash":
                if not self._validate_hash_masking(original_value, masked_value):
                    result.add_error(f"Invalid hash masking for field: {field_name}")
            
            elif masking_type == "truncate":
                if not self._validate_truncation_masking(original_value, masked_value):
                    result.add_error(f"Invalid truncation masking for field: {field_name}")
            
            elif masking_type == "substitute":
                if not self._validate_substitution_masking(original_value, masked_value):
                    result.add_error(f"Invalid substitution masking for field: {field_name}")
            
            elif masking_type == "encrypt":
                if not self._validate_encryption_masking(original_value, masked_value):
                    result.add_error(f"Invalid encryption masking for field: {field_name}")
            
            elif masking_type == "custom" and rule['validator']:
                if not rule['validator'](original_value, masked_value):
                    result.add_error(f"Custom masking validation failed for field: {field_name}")
            
            else:
                result.add_error(f"Unknown masking type: {masking_type}")
        
        except Exception as e:
            result.add_error(f"Error validating masking for {field_name}: {str(e)}")
        
        return result
    
    def _validate_hash_masking(self, original: Any, masked: Any) -> bool:
        """Validate hash-based masking."""
        if not isinstance(masked, str):
            return False
        
        # Check if it looks like a hash (hex string of expected length)
        if re.match(r'^[a-fA-F0-9]{32}$', masked):  # MD5
            return True
        if re.match(r'^[a-fA-F0-9]{64}$', masked):  # SHA256
            return True
        if re.match(r'^[a-fA-F0-9]{128}$', masked):  # SHA512
            return True
        
        # Verify it's actually a hash of the original
        original_str = str(original) if original is not None else ""
        expected_hash = hashlib.sha256(original_str.encode()).hexdigest()
        return masked == expected_hash
    
    def _validate_truncation_masking(self, original: Any, masked: Any) -> bool:
        """Validate truncation-based masking."""
        if not isinstance(original, str) or not isinstance(masked, str):
            return False
        
        # Masked value should be a prefix of original
        return original.startswith(masked) and len(masked) < len(original)
    
    def _validate_substitution_masking(self, original: Any, masked: Any) -> bool:
        """Validate substitution-based masking."""
        if not isinstance(masked, str):
            return False
        
        # Should contain masking characters (e.g., *, X)
        masking_chars = set('*X#')
        return any(char in masked for char in masking_chars)
    
    def _validate_encryption_masking(self, original: Any, masked: Any) -> bool:
        """Validate encryption-based masking."""
        if not isinstance(masked, str):
            return False
        
        # Check if it looks like base64 encoded data
        try:
            import base64
            decoded = base64.b64decode(masked)
            return len(decoded) > 0 and masked != str(original)
        except Exception:
            return False
    
    def validate_data_anonymization(self, original_data: Dict[str, Any], 
                                  anonymized_data: Dict[str, Any],
                                  k_anonymity: int = 5) -> ValidationResult:
        """Validate k-anonymity and data anonymization quality."""
        result = ValidationResult(is_valid=True)
        
        # Check that sensitive fields are properly anonymized
        sensitive_fields = ['email', 'phone', 'name', 'address', 'ssn']
        
        for field in sensitive_fields:
            if field in original_data and field in anonymized_data:
                if original_data[field] == anonymized_data[field]:
                    result.add_error(f"Sensitive field '{field}' not anonymized")
        
        # Validate k-anonymity (simplified check)
        quasi_identifiers = ['age_range', 'gender', 'zip_code_prefix', 'education_level']
        anonymized_quasi = {k: v for k, v in anonymized_data.items() if k in quasi_identifiers}
        
        if len(anonymized_quasi) < 2:
            result.add_warning("Insufficient quasi-identifiers for k-anonymity validation")
        
        result.metadata['anonymization_summary'] = {
            'sensitive_fields_anonymized': len([f for f in sensitive_fields if f in anonymized_data]),
            'quasi_identifiers': list(anonymized_quasi.keys()),
            'k_anonymity_target': k_anonymity
        }
        
        return result


class EncryptionValidator:
    """Validates encryption implementation and quality."""
    
    def __init__(self):
        self.encryption_requirements = {}
        self.key_management_checks = []
    
    def register_encryption_requirement(self, field_name: str, algorithm: str, 
                                      key_size: int, additional_checks: Optional[Dict] = None):
        """Register encryption requirements for a field."""
        self.encryption_requirements[field_name] = {
            'algorithm': algorithm,
            'key_size': key_size,
            'additional_checks': additional_checks or {}
        }
    
    def validate_field_encryption(self, field_name: str, encrypted_value: Any,
                                decryption_func: Optional[callable] = None) -> ValidationResult:
        """Validate encryption of a specific field."""
        result = ValidationResult(is_valid=True)
        
        if field_name not in self.encryption_requirements:
            result.add_warning(f"No encryption requirements defined for field: {field_name}")
            return result
        
        requirements = self.encryption_requirements[field_name]
        
        try:
            # Check if value appears to be encrypted
            if isinstance(encrypted_value, str):
                # Should not be readable text
                if self._appears_to_be_plaintext(encrypted_value):
                    result.add_error(f"Field '{field_name}' appears to be unencrypted")
                
                # Check base64 encoding (common for encrypted data)
                if not self._is_base64(encrypted_value):
                    result.add_warning(f"Field '{field_name}' not base64 encoded")
            
            # Test decryption if function provided
            if decryption_func:
                try:
                    decrypted = decryption_func(encrypted_value)
                    if decrypted == encrypted_value:
                        result.add_error(f"Decryption function returned same value for '{field_name}'")
                except Exception as e:
                    result.add_error(f"Decryption test failed for '{field_name}': {str(e)}")
            
            # Algorithm-specific checks
            algorithm = requirements['algorithm']
            if algorithm == 'AES':
                if not self._validate_aes_encryption(encrypted_value, requirements):
                    result.add_error(f"AES encryption validation failed for '{field_name}'")
            
        except Exception as e:
            result.add_error(f"Error validating encryption for '{field_name}': {str(e)}")
        
        return result
    
    def _appears_to_be_plaintext(self, value: str) -> bool:
        """Check if a string appears to be plaintext."""
        # Simple heuristics
        if len(value) < 10:
            return True
        
        # Check for common words or patterns
        common_words = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our']
        value_lower = value.lower()
        word_count = sum(1 for word in common_words if word in value_lower)
        
        if word_count > 2:
            return True
        
        # Check for readable patterns (email, phone, etc.)
        if '@' in value and '.' in value:
            return True
        
        return False
    
    def _is_base64(self, value: str) -> bool:
        """Check if string is valid base64."""
        try:
            import base64
            decoded = base64.b64decode(value)
            reencoded = base64.b64encode(decoded).decode()
            return reencoded == value
        except Exception:
            return False
    
    def _validate_aes_encryption(self, encrypted_value: Any, requirements: Dict) -> bool:
        """Validate AES encryption specifics."""
        if not isinstance(encrypted_value, str):
            return False
        
        try:
            import base64
            decoded = base64.b64decode(encrypted_value)
            
            # AES block size should be 16 bytes
            if len(decoded) % 16 != 0:
                return False
            
            # Should be longer than minimum (IV + encrypted data)
            if len(decoded) < 32:  # At least IV (16) + one block (16)
                return False
            
            return True
        except Exception:
            return False
    
    def validate_key_management(self) -> ValidationResult:
        """Validate encryption key management practices."""
        result = ValidationResult(is_valid=True)
        
        # This would integrate with your key management system
        # For now, we'll check basic requirements
        
        checks = [
            "Key rotation policy in place",
            "Keys stored securely (not in code)",
            "Access controls on keys",
            "Key backup and recovery",
            "Audit trail for key access"
        ]
        
        for check in checks:
            # In real implementation, you'd check each requirement
            result.add_warning(f"Key management check: {check} - Manual verification required")
        
        return result


class RetentionPolicyTester:
    """Tests data retention policy compliance."""
    
    def __init__(self):
        self.retention_policies = {}
        self.deletion_handlers = []
    
    def register_retention_policy(self, data_category: DataCategory, 
                                policy: RetentionPolicy, 
                                retention_days: int):
        """Register a data retention policy."""
        self.retention_policies[data_category] = {
            'policy': policy,
            'retention_days': retention_days
        }
    
    def add_deletion_handler(self, handler: callable):
        """Add a handler for data deletion testing."""
        self.deletion_handlers.append(handler)
    
    def validate_retention_compliance(self, data_records: List[Dict[str, Any]], 
                                    data_category: DataCategory) -> ValidationResult:
        """Validate retention policy compliance for data records."""
        result = ValidationResult(is_valid=True)
        
        if data_category not in self.retention_policies:
            result.add_error(f"No retention policy defined for category: {data_category.value}")
            return result
        
        policy_config = self.retention_policies[data_category]
        retention_days = policy_config['retention_days']
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        expired_records = []
        compliant_records = []
        
        for record in data_records:
            created_at = record.get('created_at')
            if not created_at:
                result.add_warning(f"Record missing created_at timestamp: {record.get('id', 'unknown')}")
                continue
            
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    result.add_error(f"Invalid timestamp format in record: {record.get('id', 'unknown')}")
                    continue
            
            if created_at < cutoff_date:
                expired_records.append(record)
            else:
                compliant_records.append(record)
        
        if expired_records:
            result.add_error(f"Found {len(expired_records)} records exceeding retention period")
        
        result.metadata.update({
            'total_records': len(data_records),
            'expired_records': len(expired_records),
            'compliant_records': len(compliant_records),
            'retention_days': retention_days,
            'cutoff_date': cutoff_date.isoformat()
        })
        
        return result
    
    def test_data_deletion(self, user_id: str, data_categories: List[DataCategory]) -> ValidationResult:
        """Test data deletion functionality."""
        result = ValidationResult(is_valid=True)
        
        deletion_results = {}
        
        for category in data_categories:
            try:
                # Test deletion for each category
                deletion_successful = True
                error_message = None
                
                for handler in self.deletion_handlers:
                    try:
                        handler_result = handler(user_id, category)
                        if not handler_result:
                            deletion_successful = False
                            error_message = f"Deletion handler failed for {category.value}"
                            break
                    except Exception as e:
                        deletion_successful = False
                        error_message = f"Deletion handler error: {str(e)}"
                        break
                
                deletion_results[category.value] = {
                    'successful': deletion_successful,
                    'error': error_message
                }
                
                if not deletion_successful:
                    result.add_error(f"Data deletion failed for category {category.value}: {error_message}")
            
            except Exception as e:
                result.add_error(f"Error testing deletion for {category.value}: {str(e)}")
        
        result.metadata['deletion_results'] = deletion_results
        return result
    
    def validate_gdpr_compliance(self, user_data: Dict[str, Any]) -> ValidationResult:
        """Validate GDPR compliance for user data."""
        result = ValidationResult(is_valid=True)
        
        gdpr_requirements = [
            'consent_recorded',
            'data_purpose_specified',
            'retention_period_defined',
            'deletion_capability',
            'data_portability',
            'privacy_notice_provided'
        ]
        
        compliance_status = {}
        
        for requirement in gdpr_requirements:
            # Check each GDPR requirement
            if requirement == 'consent_recorded':
                consent_present = 'consent' in user_data and user_data['consent'] is not None
                compliance_status[requirement] = consent_present
                if not consent_present:
                    result.add_error("User consent not properly recorded")
            
            elif requirement == 'data_purpose_specified':
                purpose_present = 'data_purpose' in user_data or 'processing_purposes' in user_data
                compliance_status[requirement] = purpose_present
                if not purpose_present:
                    result.add_error("Data processing purpose not specified")
            
            elif requirement == 'retention_period_defined':
                retention_present = 'retention_until' in user_data or 'data_retention_policy' in user_data
                compliance_status[requirement] = retention_present
                if not retention_present:
                    result.add_warning("Data retention period not clearly defined")
            
            else:
                # For other requirements, assume they need manual verification
                compliance_status[requirement] = None
                result.add_warning(f"GDPR requirement '{requirement}' requires manual verification")
        
        result.metadata['gdpr_compliance'] = compliance_status
        return result
