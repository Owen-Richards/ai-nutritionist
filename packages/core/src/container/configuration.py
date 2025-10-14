"""
Configuration Management
=======================

Environment-specific configuration, secrets, and feature flags.
"""

import os
import json
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import boto3
from botocore.exceptions import ClientError


class Environment(Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    table_name: str = "ai-nutritionist-users"
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None  # For local development
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        return cls(
            table_name=data.get('table_name', cls.table_name),
            region=data.get('region', cls.region),
            endpoint_url=data.get('endpoint_url')
        )


@dataclass
class AIConfig:
    """AI service configuration."""
    model_name: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region: str = "us-east-1"
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout_seconds: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIConfig':
        return cls(
            model_name=data.get('model_name', cls.model_name),
            region=data.get('region', cls.region),
            max_tokens=int(data.get('max_tokens', cls.max_tokens)),
            temperature=float(data.get('temperature', cls.temperature)),
            timeout_seconds=int(data.get('timeout_seconds', cls.timeout_seconds))
        )


@dataclass
class APIConfig:
    """API configuration."""
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    debug: bool = False
    rate_limit: int = 100
    rate_limit_window: int = 60  # seconds
    max_request_size: int = 1024 * 1024  # 1MB
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIConfig':
        origins = data.get('cors_origins', cls.cors_origins)
        if isinstance(origins, str):
            origins = [origin.strip() for origin in origins.split(',')]
        
        return cls(
            cors_origins=origins,
            debug=bool(data.get('debug', cls.debug)),
            rate_limit=int(data.get('rate_limit', cls.rate_limit)),
            rate_limit_window=int(data.get('rate_limit_window', cls.rate_limit_window)),
            max_request_size=int(data.get('max_request_size', cls.max_request_size))
        )


@dataclass
class MessagingConfig:
    """Messaging configuration."""
    aws_region: str = "us-east-1"
    phone_number: Optional[str] = None
    application_id: Optional[str] = None
    sender_id: str = "AI-Nutritionist"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessagingConfig':
        return cls(
            aws_region=data.get('aws_region', cls.aws_region),
            phone_number=data.get('phone_number'),
            application_id=data.get('application_id'),
            sender_id=data.get('sender_id', cls.sender_id)
        )


@dataclass
class CacheConfig:
    """Caching configuration."""
    redis_url: Optional[str] = None
    default_ttl: int = 3600  # 1 hour
    max_memory: str = "100mb"
    eviction_policy: str = "allkeys-lru"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheConfig':
        return cls(
            redis_url=data.get('redis_url'),
            default_ttl=int(data.get('default_ttl', cls.default_ttl)),
            max_memory=data.get('max_memory', cls.max_memory),
            eviction_policy=data.get('eviction_policy', cls.eviction_policy)
        )


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    log_level: str = "INFO"
    cloudwatch_log_group: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoringConfig':
        return cls(
            metrics_enabled=bool(data.get('metrics_enabled', cls.metrics_enabled)),
            tracing_enabled=bool(data.get('tracing_enabled', cls.tracing_enabled)),
            log_level=data.get('log_level', cls.log_level),
            cloudwatch_log_group=data.get('cloudwatch_log_group')
        )


@dataclass
class FeatureFlags:
    """Feature flag configuration."""
    experimental_features: bool = False
    advanced_analytics: bool = True
    community_features: bool = True
    premium_features: bool = True
    ai_recommendations: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeatureFlags':
        return cls(
            experimental_features=bool(data.get('experimental_features', cls.experimental_features)),
            advanced_analytics=bool(data.get('advanced_analytics', cls.advanced_analytics)),
            community_features=bool(data.get('community_features', cls.community_features)),
            premium_features=bool(data.get('premium_features', cls.premium_features)),
            ai_recommendations=bool(data.get('ai_recommendations', cls.ai_recommendations))
        )


@dataclass
class ApplicationConfig:
    """Main application configuration."""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    version: str = "1.0.0"
    
    # Service configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    api: APIConfig = field(default_factory=APIConfig)
    messaging: MessagingConfig = field(default_factory=MessagingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Feature flags
    features: FeatureFlags = field(default_factory=FeatureFlags)
    
    @classmethod
    def from_environment(cls) -> 'ApplicationConfig':
        """Create configuration from environment variables."""
        env_str = os.getenv('ENVIRONMENT', 'development').lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        return cls(
            environment=environment,
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            version=os.getenv('APP_VERSION', '1.0.0'),
            database=DatabaseConfig.from_dict({
                'table_name': os.getenv('DYNAMODB_TABLE_NAME'),
                'region': os.getenv('AWS_REGION'),
                'endpoint_url': os.getenv('DYNAMODB_ENDPOINT_URL')
            }),
            ai=AIConfig.from_dict({
                'model_name': os.getenv('AI_MODEL_NAME'),
                'region': os.getenv('AWS_REGION'),
                'max_tokens': os.getenv('AI_MAX_TOKENS'),
                'temperature': os.getenv('AI_TEMPERATURE'),
                'timeout_seconds': os.getenv('AI_TIMEOUT_SECONDS')
            }),
            api=APIConfig.from_dict({
                'cors_origins': os.getenv('CORS_ORIGINS'),
                'debug': os.getenv('API_DEBUG'),
                'rate_limit': os.getenv('RATE_LIMIT'),
                'rate_limit_window': os.getenv('RATE_LIMIT_WINDOW'),
                'max_request_size': os.getenv('MAX_REQUEST_SIZE')
            }),
            messaging=MessagingConfig.from_dict({
                'aws_region': os.getenv('AWS_REGION'),
                'phone_number': os.getenv('MESSAGING_PHONE_NUMBER'),
                'application_id': os.getenv('MESSAGING_APPLICATION_ID'),
                'sender_id': os.getenv('MESSAGING_SENDER_ID')
            }),
            cache=CacheConfig.from_dict({
                'redis_url': os.getenv('REDIS_URL'),
                'default_ttl': os.getenv('CACHE_DEFAULT_TTL'),
                'max_memory': os.getenv('CACHE_MAX_MEMORY'),
                'eviction_policy': os.getenv('CACHE_EVICTION_POLICY')
            }),
            monitoring=MonitoringConfig.from_dict({
                'metrics_enabled': os.getenv('METRICS_ENABLED'),
                'tracing_enabled': os.getenv('TRACING_ENABLED'),
                'log_level': os.getenv('LOG_LEVEL'),
                'cloudwatch_log_group': os.getenv('CLOUDWATCH_LOG_GROUP')
            }),
            features=FeatureFlags.from_dict({
                'experimental_features': os.getenv('FEATURE_EXPERIMENTAL'),
                'advanced_analytics': os.getenv('FEATURE_ADVANCED_ANALYTICS'),
                'community_features': os.getenv('FEATURE_COMMUNITY'),
                'premium_features': os.getenv('FEATURE_PREMIUM'),
                'ai_recommendations': os.getenv('FEATURE_AI_RECOMMENDATIONS')
            })
        )


class ConfigurationManager:
    """Manages application configuration with dynamic updates."""
    
    def __init__(self, use_parameter_store: bool = True):
        self.use_parameter_store = use_parameter_store
        self._config_cache: Dict[str, Any] = {}
        self._ssm_client = None
        
        if use_parameter_store:
            try:
                self._ssm_client = boto3.client('ssm')
            except Exception:
                self.use_parameter_store = False
    
    def get_configuration(self, config_class: type, prefix: str = None) -> Any:
        """Get configuration instance of specified type."""
        if prefix is None:
            prefix = f"/ai-nutritionist/{config_class.__name__.lower().replace('config', '')}"
        
        # Get configuration from Parameter Store
        config_data = {}
        if self.use_parameter_store:
            config_data = self._get_parameters_by_path(prefix)
        
        # Merge with environment variables
        env_data = self._get_environment_variables(prefix)
        config_data.update(env_data)
        
        # Create configuration instance
        if hasattr(config_class, 'from_dict'):
            return config_class.from_dict(config_data)
        else:
            return config_class(**config_data)
    
    def _get_parameters_by_path(self, path: str) -> Dict[str, Any]:
        """Get parameters from AWS Parameter Store by path."""
        if not self._ssm_client:
            return {}
        
        try:
            paginator = self._ssm_client.get_paginator('get_parameters_by_path')
            page_iterator = paginator.paginate(
                Path=path,
                Recursive=True,
                WithDecryption=True
            )
            
            parameters = {}
            for page in page_iterator:
                for param in page['Parameters']:
                    # Remove path prefix and convert to key
                    key = param['Name'][len(path):].lstrip('/').replace('/', '_')
                    parameters[key] = param['Value']
            
            return parameters
        except ClientError:
            return {}
    
    def _get_environment_variables(self, prefix: str) -> Dict[str, Any]:
        """Get environment variables with prefix."""
        env_prefix = prefix.replace('/', '_').replace('-', '_').upper()
        env_vars = {}
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lstrip('_').lower()
                env_vars[config_key] = value
        
        return env_vars
    
    def update_configuration(self, path: str, value: Any, description: str = None) -> bool:
        """Update configuration in Parameter Store."""
        if not self._ssm_client:
            return False
        
        try:
            kwargs = {
                'Name': path,
                'Value': str(value),
                'Type': 'String',
                'Overwrite': True
            }
            
            if description:
                kwargs['Description'] = description
            
            self._ssm_client.put_parameter(**kwargs)
            
            # Update local cache
            self._config_cache[path] = value
            return True
        except ClientError:
            return False
    
    def get_feature_flag(self, flag_name: str, default: bool = False) -> bool:
        """Get feature flag value."""
        path = f"/ai-nutritionist/features/{flag_name}"
        
        if path in self._config_cache:
            return bool(self._config_cache[path])
        
        # Try Parameter Store
        if self._ssm_client:
            try:
                response = self._ssm_client.get_parameter(Name=path)
                value = response['Parameter']['Value'].lower() == 'true'
                self._config_cache[path] = value
                return value
            except ClientError:
                pass
        
        # Try environment variable
        env_key = f"FEATURE_{flag_name.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value.lower() == 'true'
        
        return default
    
    def set_feature_flag(self, flag_name: str, enabled: bool, description: str = None) -> bool:
        """Set feature flag value."""
        path = f"/ai-nutritionist/features/{flag_name}"
        return self.update_configuration(path, enabled, description)
    
    def reload_configuration(self) -> None:
        """Reload configuration from Parameter Store."""
        self._config_cache.clear()


# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager

def get_application_config() -> ApplicationConfig:
    """Get application configuration."""
    return ApplicationConfig.from_environment()
