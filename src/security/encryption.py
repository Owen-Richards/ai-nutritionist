"""
Encryption and hashing services for data protection.

Provides comprehensive encryption following OWASP guidelines:
- AES encryption for data at rest
- Key derivation and management
- Secure password hashing with Argon2
- PII handling and tokenization
"""

import os
import secrets
import base64
import hashlib
from typing import Optional, Dict, Any, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from passlib.context import CryptContext
from passlib.handlers.argon2 import argon2

from ..services.infrastructure.secrets_manager import SecretsManager


class EncryptionError(Exception):
    """Custom encryption error."""
    pass


class KeyDerivation:
    """Key derivation utilities."""
    
    @staticmethod
    def derive_key_pbkdf2(password: bytes, salt: bytes, iterations: int = 100000) -> bytes:
        """Derive key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password)
    
    @staticmethod
    def derive_key_scrypt(password: bytes, salt: bytes, n: int = 32768, 
                         r: int = 8, p: int = 1) -> bytes:
        """Derive key using Scrypt."""
        kdf = Scrypt(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            n=n,
            r=r,
            p=p,
        )
        return kdf.derive(password)
    
    @staticmethod
    def generate_salt(length: int = 32) -> bytes:
        """Generate cryptographically secure salt."""
        return secrets.token_bytes(length)


class AESEncryption:
    """AES encryption utilities."""
    
    def __init__(self, key: bytes):
        """Initialize with 256-bit key."""
        if len(key) != 32:
            raise EncryptionError("Key must be 32 bytes for AES-256")
        self.key = key
    
    def encrypt(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        """Encrypt data with AES-256-GCM."""
        # Generate random IV
        iv = secrets.token_bytes(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        # Encrypt and get authentication tag
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Combine IV + tag + ciphertext
        encrypted_data = iv + encryptor.tag + ciphertext
        
        return encrypted_data, iv
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt AES-256-GCM data."""
        if len(encrypted_data) < 32:  # IV(16) + tag(16) minimum
            raise EncryptionError("Invalid encrypted data length")
        
        # Extract components
        iv = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        
        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")


class FernetEncryption:
    """Fernet encryption (simpler alternative to AES)."""
    
    def __init__(self, key: Optional[bytes] = None):
        """Initialize with key or generate new one."""
        if key:
            self.key = key
            self.fernet = Fernet(key)
        else:
            self.key = Fernet.generate_key()
            self.fernet = Fernet(self.key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt string data."""
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")
    
    def get_key(self) -> str:
        """Get base64-encoded key."""
        return base64.urlsafe_b64encode(self.key).decode()


class HashingService:
    """Secure hashing service."""
    
    def __init__(self):
        # Configure Argon2 for password hashing
        self.pwd_context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__rounds=3,
            argon2__memory_cost=65536,  # 64MB
            argon2__parallelism=1,
            argon2__hash_len=32
        )
    
    def hash_password(self, password: str) -> str:
        """Hash password with Argon2."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, password: str, hash_value: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(password, hash_value)
    
    def hash_data(self, data: str, algorithm: str = "sha256") -> str:
        """Hash data with specified algorithm."""
        data_bytes = data.encode('utf-8')
        
        if algorithm == "sha256":
            hash_obj = hashlib.sha256(data_bytes)
        elif algorithm == "sha512":
            hash_obj = hashlib.sha512(data_bytes)
        elif algorithm == "blake2b":
            hash_obj = hashlib.blake2b(data_bytes)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return hash_obj.hexdigest()
    
    def hash_with_salt(self, data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash data with salt."""
        if not salt:
            salt = secrets.token_hex(32)
        
        salted_data = data + salt
        hash_value = self.hash_data(salted_data)
        
        return hash_value, salt
    
    def verify_hash_with_salt(self, data: str, hash_value: str, salt: str) -> bool:
        """Verify data against hash with salt."""
        computed_hash, _ = self.hash_with_salt(data, salt)
        return secrets.compare_digest(computed_hash, hash_value)


class PIITokenizer:
    """PII tokenization service for data protection."""
    
    def __init__(self, encryption_service: 'EncryptionService'):
        self.encryption = encryption_service
        self.token_prefix = "tok_"
    
    def tokenize_pii(self, pii_data: str, data_type: str = "generic") -> str:
        """Replace PII with secure token."""
        # Encrypt the PII data
        encrypted = self.encryption.encrypt_string(pii_data)
        
        # Create token
        token_id = secrets.token_urlsafe(16)
        token = f"{self.token_prefix}{data_type}_{token_id}"
        
        # Store mapping (in production, use secure database)
        self._store_token_mapping(token, encrypted)
        
        return token
    
    def detokenize_pii(self, token: str) -> Optional[str]:
        """Retrieve original PII from token."""
        if not token.startswith(self.token_prefix):
            return None
        
        # Retrieve encrypted data
        encrypted_data = self._get_token_mapping(token)
        if not encrypted_data:
            return None
        
        # Decrypt and return
        return self.encryption.decrypt_string(encrypted_data)
    
    def _store_token_mapping(self, token: str, encrypted_data: str):
        """Store token to encrypted data mapping."""
        # Implement with secure database storage
        pass
    
    def _get_token_mapping(self, token: str) -> Optional[str]:
        """Get encrypted data for token."""
        # Implement with secure database lookup
        pass


class EncryptionService:
    """Main encryption service."""
    
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
        self.hashing = HashingService()
        
        # Get or generate encryption keys
        self.master_key = self._get_master_key()
        self.aes_encryption = AESEncryption(self.master_key)
        self.fernet_encryption = FernetEncryption(self._get_fernet_key())
        
        # Initialize PII tokenizer
        self.pii_tokenizer = PIITokenizer(self)
    
    def _get_master_key(self) -> bytes:
        """Get master encryption key."""
        key = self.secrets_manager.get_secret(
            "master_encryption_key", 
            accessed_by="encryption_service"
        )
        
        if isinstance(key, str):
            return base64.b64decode(key)
        return key
    
    def _get_fernet_key(self) -> bytes:
        """Get Fernet encryption key."""
        key = self.secrets_manager.get_secret(
            "fernet_encryption_key",
            accessed_by="encryption_service"
        )
        
        if isinstance(key, str):
            return base64.urlsafe_b64decode(key)
        return key
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt string using Fernet (URL-safe)."""
        return self.fernet_encryption.encrypt(plaintext)
    
    def decrypt_string(self, encrypted_data: str) -> str:
        """Decrypt string using Fernet."""
        return self.fernet_encryption.decrypt(encrypted_data)
    
    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        """Encrypt bytes using AES-256-GCM."""
        encrypted_data, _ = self.aes_encryption.encrypt(plaintext)
        return encrypted_data
    
    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt bytes using AES-256-GCM."""
        return self.aes_encryption.decrypt(encrypted_data)
    
    def encrypt_field(self, field_name: str, value: str, user_id: str) -> str:
        """Encrypt specific field with user-specific key derivation."""
        # Derive field-specific key
        salt = self._get_field_salt(field_name, user_id)
        field_key = KeyDerivation.derive_key_pbkdf2(
            self.master_key, salt, iterations=100000
        )
        
        # Encrypt with field-specific key
        field_encryption = AESEncryption(field_key)
        encrypted_data, _ = field_encryption.encrypt(value.encode())
        
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_field(self, field_name: str, encrypted_value: str, user_id: str) -> str:
        """Decrypt specific field with user-specific key derivation."""
        # Derive field-specific key
        salt = self._get_field_salt(field_name, user_id)
        field_key = KeyDerivation.derive_key_pbkdf2(
            self.master_key, salt, iterations=100000
        )
        
        # Decrypt with field-specific key
        field_encryption = AESEncryption(field_key)
        encrypted_data = base64.b64decode(encrypted_value)
        decrypted_bytes = field_encryption.decrypt(encrypted_data)
        
        return decrypted_bytes.decode()
    
    def _get_field_salt(self, field_name: str, user_id: str) -> bytes:
        """Get or generate field-specific salt."""
        salt_key = f"field_salt_{field_name}_{user_id}"
        
        # Try to get existing salt
        salt = self.secrets_manager.get_secret(salt_key, accessed_by="encryption_service")
        
        if not salt:
            # Generate new salt
            salt = KeyDerivation.generate_salt()
            self.secrets_manager.store_secret(
                salt_key, 
                base64.b64encode(salt).decode(),
                accessed_by="encryption_service"
            )
        elif isinstance(salt, str):
            salt = base64.b64decode(salt)
        
        return salt
    
    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """Encrypt JSON data."""
        import json
        json_str = json.dumps(data, ensure_ascii=False)
        return self.encrypt_string(json_str)
    
    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt JSON data."""
        import json
        json_str = self.decrypt_string(encrypted_data)
        return json.loads(json_str)
    
    def generate_key_pair(self) -> Tuple[str, str]:
        """Generate new encryption key pair."""
        # Generate Fernet key
        fernet_key = Fernet.generate_key()
        
        # Generate AES key
        aes_key = secrets.token_bytes(32)
        
        return (
            base64.urlsafe_b64encode(fernet_key).decode(),
            base64.b64encode(aes_key).decode()
        )
    
    def rotate_keys(self):
        """Rotate encryption keys."""
        # Generate new keys
        new_fernet_key, new_aes_key = self.generate_key_pair()
        
        # Store new keys
        self.secrets_manager.store_secret(
            "fernet_encryption_key",
            new_fernet_key,
            accessed_by="encryption_service"
        )
        
        self.secrets_manager.store_secret(
            "master_encryption_key",
            new_aes_key,
            accessed_by="encryption_service"
        )
        
        # Re-initialize encryption services
        self.fernet_encryption = FernetEncryption(
            base64.urlsafe_b64decode(new_fernet_key)
        )
        self.aes_encryption = AESEncryption(
            base64.b64decode(new_aes_key)
        )
    
    def get_key_info(self) -> Dict[str, Any]:
        """Get information about current keys (for rotation tracking)."""
        return {
            "fernet_key_created": "timestamp_from_secrets_manager",
            "aes_key_created": "timestamp_from_secrets_manager",
            "last_rotation": "timestamp_from_secrets_manager"
        }
