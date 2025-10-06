"""
G3 - Secrets Management & Security
Secure secrets management with key rotation, audit logging, and encryption.
"""

import os
import json
import time
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from pathlib import Path

# Try importing optional dependencies
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    boto3 = None

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class SecretType(str, Enum):
    """Types of secrets."""
    API_KEY = "api_key"
    DATABASE_URL = "database_url"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"
    SERVICE_ACCOUNT = "service_account"
    CERTIFICATE = "certificate"
    WEBHOOK_SECRET = "webhook_secret"


class RotationStatus(str, Enum):
    """Secret rotation status."""
    ACTIVE = "active"
    PENDING_ROTATION = "pending_rotation"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class AccessLevel(str, Enum):
    """Access levels for secrets."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    name: str
    secret_type: SecretType
    created_at: datetime
    last_accessed: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    rotation_interval_days: Optional[int] = None
    status: RotationStatus = RotationStatus.ACTIVE
    tags: Dict[str, str] = field(default_factory=dict)
    access_count: int = 0


@dataclass
class AccessAuditLog:
    """Audit log entry for secret access."""
    secret_name: str
    accessed_by: str  # service or user identifier
    access_type: str  # read, write, rotate, delete
    timestamp: datetime
    ip_address: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class EncryptionConfig:
    """Configuration for encryption operations."""
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    iterations: int = 100000
    salt_length: int = 32
    iv_length: int = 12


class LocalEncryption:
    """Local encryption/decryption utilities."""
    
    def __init__(self, master_key: Optional[str] = None):
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography package required for encryption")
        
        self.config = EncryptionConfig()
        
        # Generate or use provided master key
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._generate_master_key()
    
    def _generate_master_key(self) -> bytes:
        """Generate a new master key."""
        return secrets.token_bytes(32)  # 256-bit key
    
    def encrypt(self, plaintext: str, password: Optional[str] = None) -> str:
        """Encrypt plaintext with optional password."""
        data = plaintext.encode()
        
        # Generate salt and IV
        salt = secrets.token_bytes(self.config.salt_length)
        iv = secrets.token_bytes(self.config.iv_length)
        
        # Derive key
        key = self._derive_key(password or self.master_key, salt)
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Combine all components
        encrypted_data = salt + iv + encryptor.tag + ciphertext
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str, password: Optional[str] = None) -> str:
        """Decrypt data with optional password."""
        try:
            data = base64.b64decode(encrypted_data.encode())
            
            # Extract components
            salt = data[:self.config.salt_length]
            iv = data[self.config.salt_length:self.config.salt_length + self.config.iv_length]
            tag_start = self.config.salt_length + self.config.iv_length
            tag = data[tag_start:tag_start + 16]  # GCM tag is 16 bytes
            ciphertext = data[tag_start + 16:]
            
            # Derive key
            key = self._derive_key(password or self.master_key, salt)
            
            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def _derive_key(self, password: Union[str, bytes], salt: bytes) -> bytes:
        """Derive encryption key from password and salt."""
        if isinstance(password, str):
            password = password.encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.iterations,
        )
        return kdf.derive(password)


class AWSSecretsBackend:
    """AWS Secrets Manager backend."""
    
    def __init__(self, region_name: str = "us-east-1"):
        if not AWS_AVAILABLE:
            raise ImportError("boto3 required for AWS Secrets Manager")
        
        self.client = boto3.client('secretsmanager', region_name=region_name)
        self.region = region_name
    
    def store_secret(self, name: str, value: str, description: str = "") -> bool:
        """Store secret in AWS Secrets Manager."""
        try:
            self.client.create_secret(
                Name=name,
                SecretString=value,
                Description=description
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                # Update existing secret
                return self.update_secret(name, value)
            raise e
    
    def get_secret(self, name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self.client.get_secret_value(SecretName=name)
            return response.get('SecretString')
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise e
    
    def update_secret(self, name: str, value: str) -> bool:
        """Update existing secret."""
        try:
            self.client.update_secret(
                SecretId=name,
                SecretString=value
            )
            return True
        except ClientError:
            return False
    
    def delete_secret(self, name: str, force: bool = False) -> bool:
        """Delete secret (with optional force delete)."""
        try:
            if force:
                self.client.delete_secret(
                    SecretId=name,
                    ForceDeleteWithoutRecovery=True
                )
            else:
                self.client.delete_secret(SecretId=name)
            return True
        except ClientError:
            return False
    
    def list_secrets(self) -> List[str]:
        """List all secret names."""
        try:
            response = self.client.list_secrets()
            return [secret['Name'] for secret in response.get('SecretList', [])]
        except ClientError:
            return []


class LocalFileBackend:
    """Local file-based secrets backend (encrypted)."""
    
    def __init__(self, secrets_dir: str = ".secrets", encryption_key: Optional[str] = None):
        self.secrets_dir = Path(secrets_dir)
        self.secrets_dir.mkdir(exist_ok=True, mode=0o700)  # Secure directory
        
        self.encryption = LocalEncryption(encryption_key)
        self.metadata_file = self.secrets_dir / "metadata.json"
        
        # Load metadata
        self._metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, SecretMetadata]:
        """Load secrets metadata from file."""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            metadata = {}
            for name, meta_dict in data.items():
                # Convert datetime strings back to datetime objects
                meta_dict['created_at'] = datetime.fromisoformat(meta_dict['created_at'])
                if meta_dict.get('last_accessed'):
                    meta_dict['last_accessed'] = datetime.fromisoformat(meta_dict['last_accessed'])
                if meta_dict.get('last_rotated'):
                    meta_dict['last_rotated'] = datetime.fromisoformat(meta_dict['last_rotated'])
                
                metadata[name] = SecretMetadata(**meta_dict)
            
            return metadata
        except Exception:
            return {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        data = {}
        for name, metadata in self._metadata.items():
            meta_dict = {
                'name': metadata.name,
                'secret_type': metadata.secret_type,
                'created_at': metadata.created_at.isoformat(),
                'last_accessed': metadata.last_accessed.isoformat() if metadata.last_accessed else None,
                'last_rotated': metadata.last_rotated.isoformat() if metadata.last_rotated else None,
                'rotation_interval_days': metadata.rotation_interval_days,
                'status': metadata.status,
                'tags': metadata.tags,
                'access_count': metadata.access_count
            }
            data[name] = meta_dict
        
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def store_secret(self, name: str, value: str, secret_type: SecretType = SecretType.API_KEY) -> bool:
        """Store encrypted secret to file."""
        try:
            # Encrypt the secret
            encrypted_value = self.encryption.encrypt(value)
            
            # Save to file
            secret_file = self.secrets_dir / f"{name}.enc"
            with open(secret_file, 'w') as f:
                f.write(encrypted_value)
            
            # Update metadata
            self._metadata[name] = SecretMetadata(
                name=name,
                secret_type=secret_type,
                created_at=datetime.utcnow()
            )
            self._save_metadata()
            
            return True
        except Exception:
            return False
    
    def get_secret(self, name: str) -> Optional[str]:
        """Get and decrypt secret from file."""
        secret_file = self.secrets_dir / f"{name}.enc"
        if not secret_file.exists():
            return None
        
        try:
            with open(secret_file, 'r') as f:
                encrypted_value = f.read()
            
            # Decrypt
            value = self.encryption.decrypt(encrypted_value)
            
            # Update metadata
            if name in self._metadata:
                self._metadata[name].last_accessed = datetime.utcnow()
                self._metadata[name].access_count += 1
                self._save_metadata()
            
            return value
        except Exception:
            return None
    
    def update_secret(self, name: str, value: str) -> bool:
        """Update existing secret."""
        if name not in self._metadata:
            return False
        return self.store_secret(name, value, self._metadata[name].secret_type)
    
    def delete_secret(self, name: str) -> bool:
        """Delete secret file."""
        secret_file = self.secrets_dir / f"{name}.enc"
        try:
            if secret_file.exists():
                secret_file.unlink()
            
            if name in self._metadata:
                del self._metadata[name]
                self._save_metadata()
            
            return True
        except Exception:
            return False
    
    def list_secrets(self) -> List[str]:
        """List all secret names."""
        return list(self._metadata.keys())
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get secret metadata."""
        return self._metadata.get(name)


class SecretsManager:
    """
    Comprehensive secrets management service with encryption, rotation, and audit logging.
    """
    
    def __init__(
        self,
        backend: str = "local",  # "local" or "aws"
        aws_region: str = "us-east-1",
        local_secrets_dir: str = ".secrets",
        encryption_key: Optional[str] = None,
        enable_audit_logging: bool = True
    ):
        self.enable_audit_logging = enable_audit_logging
        
        # Initialize backend
        if backend == "aws" and AWS_AVAILABLE:
            self.backend = AWSSecretsBackend(aws_region)
        else:
            self.backend = LocalFileBackend(local_secrets_dir, encryption_key)
        
        # Audit logging
        self.audit_logs: List[AccessAuditLog] = []
        self._audit_lock = threading.Lock()
        
        # Rotation scheduling
        self._rotation_scheduler = {}
        self._start_rotation_scheduler()
    
    def store_secret(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.API_KEY,
        rotation_interval_days: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None,
        accessed_by: str = "system"
    ) -> bool:
        """Store a secret with metadata."""
        try:
            success = self.backend.store_secret(name, value, secret_type.value if hasattr(self.backend, 'store_secret') else str(secret_type))
            
            # Update metadata if using local backend
            if hasattr(self.backend, '_metadata') and success:
                metadata = self.backend._metadata.get(name)
                if metadata:
                    metadata.rotation_interval_days = rotation_interval_days
                    metadata.tags = tags or {}
                    self.backend._save_metadata()
            
            # Audit log
            self._log_access(name, accessed_by, "store", success=success)
            
            # Schedule rotation if specified
            if success and rotation_interval_days:
                self._schedule_rotation(name, rotation_interval_days)
            
            return success
        except Exception as e:
            self._log_access(name, accessed_by, "store", success=False, error=str(e))
            return False
    
    def get_secret(self, name: str, accessed_by: str = "system") -> Optional[str]:
        """Get a secret value."""
        try:
            value = self.backend.get_secret(name)
            success = value is not None
            
            self._log_access(name, accessed_by, "read", success=success)
            return value
        except Exception as e:
            self._log_access(name, accessed_by, "read", success=False, error=str(e))
            return None
    
    def update_secret(self, name: str, value: str, accessed_by: str = "system") -> bool:
        """Update an existing secret."""
        try:
            success = self.backend.update_secret(name, value)
            self._log_access(name, accessed_by, "update", success=success)
            return success
        except Exception as e:
            self._log_access(name, accessed_by, "update", success=False, error=str(e))
            return False
    
    def rotate_secret(self, name: str, accessed_by: str = "system") -> bool:
        """Rotate a secret (generate new value)."""
        try:
            # Get current secret metadata
            metadata = None
            if hasattr(self.backend, 'get_metadata'):
                metadata = self.backend.get_metadata(name)
            
            if not metadata:
                return False
            
            # Generate new value based on secret type
            new_value = self._generate_secret_value(metadata.secret_type)
            
            # Update the secret
            success = self.backend.update_secret(name, new_value)
            
            if success and hasattr(self.backend, '_metadata'):
                metadata.last_rotated = datetime.utcnow()
                metadata.status = RotationStatus.ACTIVE
                self.backend._save_metadata()
            
            self._log_access(name, accessed_by, "rotate", success=success)
            return success
        except Exception as e:
            self._log_access(name, accessed_by, "rotate", success=False, error=str(e))
            return False
    
    def delete_secret(self, name: str, accessed_by: str = "system") -> bool:
        """Delete a secret."""
        try:
            success = self.backend.delete_secret(name)
            self._log_access(name, accessed_by, "delete", success=success)
            return success
        except Exception as e:
            self._log_access(name, accessed_by, "delete", success=False, error=str(e))
            return False
    
    def list_secrets(self, accessed_by: str = "system") -> List[str]:
        """List all secret names."""
        try:
            secrets = self.backend.list_secrets()
            self._log_access("*", accessed_by, "list", success=True)
            return secrets
        except Exception as e:
            self._log_access("*", accessed_by, "list", success=False, error=str(e))
            return []
    
    def get_secret_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get secret metadata."""
        if hasattr(self.backend, 'get_metadata'):
            return self.backend.get_metadata(name)
        return None
    
    def _generate_secret_value(self, secret_type: SecretType) -> str:
        """Generate a new secret value based on type."""
        if secret_type == SecretType.API_KEY:
            return secrets.token_urlsafe(32)
        elif secret_type == SecretType.JWT_SECRET:
            return secrets.token_urlsafe(64)
        elif secret_type == SecretType.ENCRYPTION_KEY:
            return base64.b64encode(secrets.token_bytes(32)).decode()
        elif secret_type == SecretType.WEBHOOK_SECRET:
            return secrets.token_hex(32)
        else:
            return secrets.token_urlsafe(32)
    
    def _log_access(
        self,
        secret_name: str,
        accessed_by: str,
        access_type: str,
        success: bool = True,
        error: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log secret access for audit trail."""
        if not self.enable_audit_logging:
            return
        
        with self._audit_lock:
            log_entry = AccessAuditLog(
                secret_name=secret_name,
                accessed_by=accessed_by,
                access_type=access_type,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                success=success,
                error_message=error
            )
            self.audit_logs.append(log_entry)
            
            # Keep only last 10000 entries
            if len(self.audit_logs) > 10000:
                self.audit_logs = self.audit_logs[-10000:]
    
    def get_audit_logs(
        self,
        secret_name: Optional[str] = None,
        accessed_by: Optional[str] = None,
        hours_back: int = 24
    ) -> List[AccessAuditLog]:
        """Get audit logs with optional filtering."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        filtered_logs = []
        for log in self.audit_logs:
            if log.timestamp < cutoff_time:
                continue
            if secret_name and log.secret_name != secret_name:
                continue
            if accessed_by and log.accessed_by != accessed_by:
                continue
            
            filtered_logs.append(log)
        
        return filtered_logs
    
    def _schedule_rotation(self, name: str, interval_days: int):
        """Schedule automatic secret rotation."""
        next_rotation = datetime.utcnow() + timedelta(days=interval_days)
        self._rotation_scheduler[name] = next_rotation
    
    def _start_rotation_scheduler(self):
        """Start background rotation scheduler."""
        def rotation_worker():
            while True:
                try:
                    current_time = datetime.utcnow()
                    for name, next_rotation in list(self._rotation_scheduler.items()):
                        if current_time >= next_rotation:
                            success = self.rotate_secret(name, "auto_rotation")
                            if success:
                                # Reschedule
                                metadata = self.get_secret_metadata(name)
                                if metadata and metadata.rotation_interval_days:
                                    self._schedule_rotation(name, metadata.rotation_interval_days)
                            del self._rotation_scheduler[name]
                except Exception as e:
                    print(f"Rotation scheduler error: {e}")
                
                time.sleep(3600)  # Check every hour
        
        thread = threading.Thread(target=rotation_worker, daemon=True)
        thread.start()
    
    def get_rotation_status(self) -> Dict[str, Any]:
        """Get status of scheduled rotations."""
        return {
            "scheduled_rotations": len(self._rotation_scheduler),
            "next_rotations": {
                name: rotation_time.isoformat()
                for name, rotation_time in self._rotation_scheduler.items()
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for secrets manager."""
        try:
            # Test backend connectivity
            secrets_count = len(self.list_secrets("health_check"))
            
            return {
                "status": "healthy",
                "backend_type": type(self.backend).__name__,
                "secrets_count": secrets_count,
                "audit_logs_count": len(self.audit_logs),
                "scheduled_rotations": len(self._rotation_scheduler),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global instance
secrets_manager = SecretsManager()

# Convenience functions
def get_secret(name: str, accessed_by: str = "application") -> Optional[str]:
    """Global function to get secret."""
    return secrets_manager.get_secret(name, accessed_by)

def store_secret(name: str, value: str, secret_type: SecretType = SecretType.API_KEY) -> bool:
    """Global function to store secret."""
    return secrets_manager.store_secret(name, value, secret_type)

@contextmanager
def secret_context(name: str, accessed_by: str = "application"):
    """Context manager for secure secret access."""
    secret_value = secrets_manager.get_secret(name, accessed_by)
    try:
        yield secret_value
    finally:
        # Could add cleanup logic here
        pass
