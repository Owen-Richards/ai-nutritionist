"""
Service Providers
================

Specialized providers for configuration, secrets, and external dependencies.
"""

import os
import json
from typing import Any, Dict, Optional, Type, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError

from .exceptions import ConfigurationException, DIException

if TYPE_CHECKING:
    from .container import Container


class ServiceProvider(ABC):
    """Abstract base class for service providers."""
    
    @abstractmethod
    def can_provide(self, service_type: Type) -> bool:
        """Check if this provider can provide the requested service type."""
        pass
    
    @abstractmethod
    def provide(self, service_type: Type, container: 'Container') -> Any:
        """Provide an instance of the requested service type."""
        pass


class ConfigurationProvider(ServiceProvider):
    """Provider for configuration values from environment variables and files."""
    
    def __init__(self, config_file: str = None, environment_prefix: str = "AI_NUTRITIONIST_"):
        self.config_file = config_file
        self.environment_prefix = environment_prefix
        self._config_cache: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file and environment."""
        # Load from file if specified
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._config_cache.update(file_config)
            except (json.JSONDecodeError, IOError) as e:
                raise ConfigurationException("config_file", f"Failed to load config file: {e}")
        
        # Load from environment variables
        for key, value in os.environ.items():
            if key.startswith(self.environment_prefix):
                config_key = key[len(self.environment_prefix):].lower()
                self._config_cache[config_key] = value
    
    def can_provide(self, service_type: Type) -> bool:
        """Check if this is a configuration request."""
        return hasattr(service_type, '__name__') and service_type.__name__.endswith('Config')
    
    def provide(self, service_type: Type, container: 'Container') -> Any:
        """Provide configuration instance."""
        try:
            # Try to instantiate the config class with available values
            if hasattr(service_type, 'from_dict'):
                return service_type.from_dict(self._config_cache)
            else:
                # Try constructor with keyword arguments
                import inspect
                sig = inspect.signature(service_type.__init__)
                kwargs = {}
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    
                    config_key = param_name.lower()
                    if config_key in self._config_cache:
                        kwargs[param_name] = self._config_cache[config_key]
                    elif param.default == inspect.Parameter.empty:
                        raise ConfigurationException(config_key, f"Required parameter {param_name} not found")
                
                return service_type(**kwargs)
        
        except Exception as e:
            raise ConfigurationException(service_type.__name__, str(e))
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        return self._config_cache.get(key.lower(), default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config_cache[key.lower()] = value


class SecretProvider(ServiceProvider):
    """Provider for secrets from AWS Parameter Store or environment."""
    
    def __init__(self, use_parameter_store: bool = True, parameter_prefix: str = "/ai-nutritionist/"):
        self.use_parameter_store = use_parameter_store
        self.parameter_prefix = parameter_prefix
        self._secret_cache: Dict[str, str] = {}
        self._ssm_client = None
        
        if use_parameter_store:
            try:
                self._ssm_client = boto3.client('ssm')
            except Exception:
                # Fall back to environment variables
                self.use_parameter_store = False
    
    def can_provide(self, service_type: Type) -> bool:
        """Check if this is a secret request."""
        return hasattr(service_type, '__name__') and 'secret' in service_type.__name__.lower()
    
    def provide(self, service_type: Type, container: 'Container') -> Any:
        """Provide secret configuration instance."""
        try:
            # Get secret values based on class attributes
            secret_values = {}
            
            for attr_name in dir(service_type):
                if not attr_name.startswith('_'):
                    secret_key = f"{self.parameter_prefix}{attr_name.lower()}"
                    secret_value = self.get_secret(secret_key)
                    if secret_value:
                        secret_values[attr_name] = secret_value
            
            return service_type(**secret_values)
        
        except Exception as e:
            raise ConfigurationException(service_type.__name__, f"Failed to load secrets: {e}")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value."""
        if key in self._secret_cache:
            return self._secret_cache[key]
        
        value = None
        
        if self.use_parameter_store and self._ssm_client:
            try:
                response = self._ssm_client.get_parameter(Name=key, WithDecryption=True)
                value = response['Parameter']['Value']
            except ClientError:
                pass  # Parameter not found
        
        # Fall back to environment variable
        if value is None:
            env_key = key.replace('/', '_').replace('-', '_').upper()
            value = os.getenv(env_key)
        
        if value:
            self._secret_cache[key] = value
        
        return value
    
    def set_secret(self, key: str, value: str, description: str = None) -> bool:
        """Set a secret value in Parameter Store."""
        if not self.use_parameter_store or not self._ssm_client:
            return False
        
        try:
            kwargs = {
                'Name': key,
                'Value': value,
                'Type': 'SecureString',
                'Overwrite': True
            }
            
            if description:
                kwargs['Description'] = description
            
            self._ssm_client.put_parameter(**kwargs)
            self._secret_cache[key] = value
            return True
        
        except ClientError:
            return False


class FactoryProvider(ServiceProvider):
    """Provider for factory-created services."""
    
    def __init__(self):
        self._factories: Dict[Type, Callable] = {}
    
    def register_factory(self, service_type: Type, factory: Callable) -> None:
        """Register a factory function for a service type."""
        self._factories[service_type] = factory
    
    def can_provide(self, service_type: Type) -> bool:
        """Check if a factory is registered for this type."""
        return service_type in self._factories
    
    def provide(self, service_type: Type, container: 'Container') -> Any:
        """Create instance using registered factory."""
        factory = self._factories[service_type]
        
        # Try to inject dependencies into factory if it accepts them
        import inspect
        sig = inspect.signature(factory)
        
        if len(sig.parameters) == 0:
            return factory()
        else:
            # Inject container as parameter if factory expects it
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param.annotation == type(container) or param_name == 'container':
                    kwargs[param_name] = container
            
            return factory(**kwargs)


class ExternalServiceProvider(ServiceProvider):
    """Provider for external services (AWS clients, etc.)."""
    
    def __init__(self):
        self._external_services: Dict[Type, Callable] = {}
        self._setup_aws_services()
    
    def _setup_aws_services(self) -> None:
        """Setup AWS service factories."""
        import boto3
        
        self._external_services.update({
            # AWS services
            boto3.Session: lambda: boto3.Session(),
            # Add other AWS services as needed
        })
    
    def can_provide(self, service_type: Type) -> bool:
        """Check if this is an external service we can provide."""
        return service_type in self._external_services
    
    def provide(self, service_type: Type, container: 'Container') -> Any:
        """Provide external service instance."""
        factory = self._external_services[service_type]
        return factory()
    
    def register_external_service(self, service_type: Type, factory: Callable) -> None:
        """Register an external service factory."""
        self._external_services[service_type] = factory
