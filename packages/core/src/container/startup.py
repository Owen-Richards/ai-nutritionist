"""
Application Startup Configuration
=================================

Complete startup configuration for the AI Nutritionist application with DI.
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.core.src.container import (
    Container, get_container, configure_container,
    injectable, singleton, scoped, transient
)
from packages.core.src.container.auto_registration import create_auto_configured_container
from packages.core.src.container.configuration import (
    get_application_config, get_config_manager,
    ApplicationConfig, Environment
)


class ApplicationBootstrap:
    """Handles application startup and DI container configuration."""
    
    def __init__(self, environment: str = None, config_path: str = None):
        self.environment = Environment(environment or os.getenv('ENVIRONMENT', 'development'))
        self.config_path = config_path
        self.container: Optional[Container] = None
        self.startup_errors: list = []
    
    def bootstrap(self) -> Container:
        """Bootstrap the application with full DI configuration."""
        print(f"🚀 Bootstrapping AI Nutritionist ({self.environment.value})")
        print("=" * 60)
        
        try:
            # Step 1: Create and configure container
            self.container = self._create_container()
            
            # Step 2: Register core services
            self._register_core_services()
            
            # Step 3: Register application services
            self._register_application_services()
            
            # Step 4: Validate container
            self._validate_container()
            
            # Step 5: Perform health checks
            self._perform_health_checks()
            
            print("✅ Application bootstrap completed successfully")
            return self.container
        
        except Exception as e:
            print(f"❌ Bootstrap failed: {e}")
            self.startup_errors.append(str(e))
            raise
    
    def _create_container(self) -> Container:
        """Create and configure the DI container."""
        print("📦 Creating DI container...")
        
        if os.getenv('AUTO_REGISTRATION', 'true').lower() == 'true':
            # Use automatic service discovery
            container = create_auto_configured_container(str(project_root))
        else:
            # Manual registration
            container = Container()
            configure_container(container)
        
        return container
    
    def _register_core_services(self) -> None:
        """Register core infrastructure services."""
        print("🔧 Registering core services...")
        
        try:
            # Health check service
            @singleton
            class HealthCheckService:
                def __init__(self, app_config: ApplicationConfig):
                    self.app_config = app_config
                
                def check_health(self) -> Dict[str, Any]:
                    return {
                        'status': 'healthy',
                        'environment': self.app_config.environment.value,
                        'version': self.app_config.version,
                        'timestamp': self._get_timestamp()
                    }
                
                def _get_timestamp(self) -> str:
                    from datetime import datetime
                    return datetime.utcnow().isoformat()
            
            self.container.register_singleton(HealthCheckService)
            
            # Logging service
            @singleton
            class LoggingService:
                def __init__(self, monitoring_config: dict):
                    self.config = monitoring_config
                    self.log_level = monitoring_config.get('log_level', 'INFO')
                
                def log(self, level: str, message: str, **kwargs):
                    print(f"[{level}] {message}")
                    if kwargs:
                        print(f"  Context: {kwargs}")
                
                def info(self, message: str, **kwargs):
                    self.log('INFO', message, **kwargs)
                
                def error(self, message: str, **kwargs):
                    self.log('ERROR', message, **kwargs)
                
                def warning(self, message: str, **kwargs):
                    self.log('WARNING', message, **kwargs)
            
            self.container.register_singleton(LoggingService)
            
            print("✅ Core services registered")
        
        except Exception as e:
            error = f"Failed to register core services: {e}"
            print(f"❌ {error}")
            self.startup_errors.append(error)
    
    def _register_application_services(self) -> None:
        """Register application-specific services."""
        print("🏗️ Registering application services...")
        
        try:
            # Example application services
            self._register_nutrition_services()
            self._register_messaging_services()
            self._register_user_services()
            
            print("✅ Application services registered")
        
        except Exception as e:
            error = f"Failed to register application services: {e}"
            print(f"❌ {error}")
            self.startup_errors.append(error)
    
    def _register_nutrition_services(self) -> None:
        """Register nutrition domain services."""
        try:
            # Basic nutrition calculator
            @injectable()
            class NutritionCalculator:
                def calculate_calories(self, weight: float, height: float, age: int) -> int:
                    # Simple BMR calculation
                    bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
                    return int(bmr * 1.5)  # Assume moderate activity
            
            # Meal planner service
            @scoped
            class MealPlannerService:
                def __init__(self, nutrition_calculator: NutritionCalculator, app_config: ApplicationConfig):
                    self.calculator = nutrition_calculator
                    self.config = app_config
                
                def create_meal_plan(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
                    calories = self.calculator.calculate_calories(
                        user_data['weight'],
                        user_data['height'],
                        user_data['age']
                    )
                    
                    return {
                        'daily_calories': calories,
                        'meals': ['breakfast', 'lunch', 'dinner'],
                        'generated_at': self._get_timestamp()
                    }
                
                def _get_timestamp(self) -> str:
                    from datetime import datetime
                    return datetime.utcnow().isoformat()
            
            self.container.register_transient(NutritionCalculator)
            self.container.register_scoped(MealPlannerService)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not register nutrition services: {e}")
    
    def _register_messaging_services(self) -> None:
        """Register messaging services."""
        try:
            @scoped
            class NotificationService:
                def __init__(self, app_config: ApplicationConfig):
                    self.config = app_config
                
                def send_notification(self, user_id: str, message: str) -> bool:
                    print(f"📧 Sending notification to {user_id}: {message}")
                    return True
            
            self.container.register_scoped(NotificationService)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not register messaging services: {e}")
    
    def _register_user_services(self) -> None:
        """Register user management services."""
        try:
            @scoped
            class UserService:
                def __init__(self, app_config: ApplicationConfig):
                    self.config = app_config
                
                def get_user(self, user_id: str) -> Dict[str, Any]:
                    return {
                        'user_id': user_id,
                        'name': f'User {user_id}',
                        'preferences': {}
                    }
                
                def create_user(self, user_data: Dict[str, Any]) -> str:
                    user_id = f"user_{len(user_data)}"
                    print(f"👤 Created user: {user_id}")
                    return user_id
            
            self.container.register_scoped(UserService)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not register user services: {e}")
    
    def _validate_container(self) -> None:
        """Validate the container configuration."""
        print("🔍 Validating container...")
        
        validation_issues = self.container.validate_services()
        
        if validation_issues:
            print("⚠️ Container validation issues:")
            for issue in validation_issues:
                print(f"  - {issue}")
                self.startup_errors.append(f"Validation: {issue}")
        else:
            print("✅ Container validation passed")
        
        # Print service summary
        service_info = self.container.get_service_info()
        print(f"📊 Registered services: {len(service_info)}")
        
        for service_name, info in service_info.items():
            print(f"  {service_name} ({info['lifetime']})")
    
    def _perform_health_checks(self) -> None:
        """Perform startup health checks."""
        print("🏥 Performing health checks...")
        
        try:
            # Test service resolution
            app_config = self.container.resolve(ApplicationConfig)
            print(f"✅ Configuration resolved: {app_config.environment.value}")
            
            # Test health check service
            health_service = self.container.try_resolve('HealthCheckService')
            if health_service:
                health = health_service.check_health()
                print(f"✅ Health check passed: {health['status']}")
            
            # Test logging service
            logging_service = self.container.try_resolve('LoggingService')
            if logging_service:
                logging_service.info("Application startup completed")
                print("✅ Logging service operational")
            
        except Exception as e:
            error = f"Health check failed: {e}"
            print(f"❌ {error}")
            self.startup_errors.append(error)
    
    def get_startup_summary(self) -> Dict[str, Any]:
        """Get startup summary information."""
        return {
            'environment': self.environment.value,
            'container_configured': self.container is not None,
            'startup_errors': self.startup_errors,
            'service_count': len(self.container.get_service_info()) if self.container else 0
        }


class ProductionBootstrap(ApplicationBootstrap):
    """Production-specific bootstrap configuration."""
    
    def __init__(self):
        super().__init__(environment='production')
    
    def _register_core_services(self) -> None:
        """Register production-specific core services."""
        super()._register_core_services()
        
        # Add production-specific services
        print("🔒 Registering production services...")
        
        @singleton
        class SecurityService:
            def __init__(self, app_config: ApplicationConfig):
                self.config = app_config
            
            def validate_request(self, request_data: Dict[str, Any]) -> bool:
                # Add security validation logic
                return True
        
        self.container.register_singleton(SecurityService)


class DevelopmentBootstrap(ApplicationBootstrap):
    """Development-specific bootstrap configuration."""
    
    def __init__(self):
        super().__init__(environment='development')
    
    def _register_core_services(self) -> None:
        """Register development-specific core services."""
        super()._register_core_services()
        
        # Add development-specific services
        print("🛠️ Registering development services...")
        
        @singleton
        class DevToolsService:
            def __init__(self, app_config: ApplicationConfig):
                self.config = app_config
            
            def enable_debug_mode(self) -> None:
                print("🐛 Debug mode enabled")
            
            def generate_test_data(self) -> Dict[str, Any]:
                return {'test': 'data'}
        
        self.container.register_singleton(DevToolsService)


def create_bootstrap(environment: str = None) -> ApplicationBootstrap:
    """Create appropriate bootstrap for environment."""
    env = environment or os.getenv('ENVIRONMENT', 'development')
    
    if env == 'production':
        return ProductionBootstrap()
    elif env == 'development':
        return DevelopmentBootstrap()
    else:
        return ApplicationBootstrap(environment=env)


# =============================================================================
# LAMBDA HANDLER INTEGRATION
# =============================================================================

def lambda_handler(event, context):
    """
    AWS Lambda handler with DI container.
    
    This shows how to integrate the DI container with serverless functions.
    """
    # Bootstrap application
    bootstrap = create_bootstrap('production')
    container = bootstrap.bootstrap()
    
    try:
        # Example: Resolve nutrition service and handle request
        meal_planner = container.resolve('MealPlannerService')
        user_service = container.resolve('UserService')
        
        # Extract user data from event
        user_data = event.get('user_data', {
            'weight': 70.0,
            'height': 175.0,
            'age': 30
        })
        
        # Process request
        meal_plan = meal_planner.create_meal_plan(user_data)
        
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'data': meal_plan
            }
        }
    
    except Exception as e:
        # Use logging service for error reporting
        logging_service = container.try_resolve('LoggingService')
        if logging_service:
            logging_service.error(f"Lambda handler error: {e}")
        
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e)
            }
        }


# =============================================================================
# FLASK APP INTEGRATION
# =============================================================================

def create_flask_app():
    """
    Create Flask application with DI container.
    
    This shows how to integrate with Flask web applications.
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Flask not available, skipping Flask integration")
        return None
    
    app = Flask(__name__)
    
    # Bootstrap DI container
    bootstrap = create_bootstrap()
    container = bootstrap.bootstrap()
    
    # Store container in app context
    app.container = container
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        health_service = container.try_resolve('HealthCheckService')
        if health_service:
            return jsonify(health_service.check_health())
        else:
            return jsonify({'status': 'unknown'})
    
    @app.route('/nutrition/plan', methods=['POST'])
    def create_nutrition_plan():
        """Create nutrition plan endpoint."""
        try:
            # Resolve services from container
            meal_planner = container.resolve('MealPlannerService')
            
            # Get request data
            user_data = request.json
            
            # Process request
            plan = meal_planner.create_meal_plan(user_data)
            
            return jsonify({
                'success': True,
                'data': plan
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/services')
    def list_services():
        """List all registered services."""
        service_info = container.get_service_info()
        return jsonify(service_info)
    
    return app


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for standalone application."""
    print("🚀 AI Nutritionist - DI Container Bootstrap")
    print("=" * 60)
    
    # Create and run bootstrap
    bootstrap = create_bootstrap()
    container = bootstrap.bootstrap()
    
    # Print summary
    summary = bootstrap.get_startup_summary()
    print(f"\n📊 Startup Summary:")
    print(f"  Environment: {summary['environment']}")
    print(f"  Services: {summary['service_count']}")
    print(f"  Errors: {len(summary['startup_errors'])}")
    
    if summary['startup_errors']:
        print("  Issues:")
        for error in summary['startup_errors']:
            print(f"    - {error}")
    
    # Example usage
    print("\n🧪 Testing service resolution...")
    
    try:
        # Test configuration resolution
        config = container.resolve(ApplicationConfig)
        print(f"✅ Config resolved: {config.environment.value}")
        
        # Test service resolution
        meal_planner = container.try_resolve('MealPlannerService')
        if meal_planner:
            plan = meal_planner.create_meal_plan({
                'weight': 70.0,
                'height': 175.0,
                'age': 30
            })
            print(f"✅ Meal plan created: {plan['daily_calories']} calories")
        
        print("\n🎉 Application ready for use!")
        
    except Exception as e:
        print(f"❌ Service resolution failed: {e}")


if __name__ == "__main__":
    main()
