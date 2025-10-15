"""
External service interfaces for domain integration
Following hexagonal architecture principles
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class NutritionAPIService(ABC):
    """Interface for external nutrition API services (e.g., Edamam)"""
    
    @abstractmethod
    async def search_recipes(self, query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search for recipes with dietary filters"""
        pass
    
    @abstractmethod
    async def analyze_nutrition(self, ingredients: List[str]) -> Dict[str, Any]:
        """Analyze nutritional content of ingredients"""
        pass
    
    @abstractmethod
    async def get_food_database_info(self, food_query: str) -> Dict[str, Any]:
        """Get food database information"""
        pass


class AIService(ABC):
    """Interface for AI/LLM services"""
    
    @abstractmethod
    async def generate_meal_plan(self, user_preferences: Dict[str, Any], context: str) -> str:
        """Generate personalized meal plan"""
        pass
    
    @abstractmethod
    async def generate_nutrition_advice(self, query: str, user_context: Dict[str, Any]) -> str:
        """Generate nutrition advice response"""
        pass
    
    @abstractmethod
    async def analyze_dietary_patterns(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user dietary patterns"""
        pass


class MessagingService(ABC):
    """Interface for messaging services (SMS, WhatsApp, etc.)"""
    
    @abstractmethod
    async def send_message(self, to: str, message: str, channel: str = "sms") -> bool:
        """Send message to user"""
        pass
    
    @abstractmethod
    async def send_rich_message(self, to: str, content: Dict[str, Any], channel: str = "whatsapp") -> bool:
        """Send rich media message"""
        pass


class PaymentService(ABC):
    """Interface for payment processing services"""
    
    @abstractmethod
    async def create_subscription(self, user_id: str, plan: str) -> Dict[str, Any]:
        """Create user subscription"""
        pass
    
    @abstractmethod
    async def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment transaction"""
        pass
    
    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel user subscription"""
        pass


class ConfigurationService(ABC):
    """Interface for configuration and secrets management"""
    
    @abstractmethod
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret value"""
        pass
    
    @abstractmethod
    async def get_config(self, config_key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass


class MonitoringService(ABC):
    """Interface for monitoring and observability"""
    
    @abstractmethod
    async def track_metric(self, metric_name: str, value: float, dimensions: Dict[str, str] = None) -> bool:
        """Track custom metric"""
        pass
    
    @abstractmethod
    async def log_event(self, event_name: str, data: Dict[str, Any]) -> bool:
        """Log structured event"""
        pass
    
    @abstractmethod
    async def create_alarm(self, alarm_config: Dict[str, Any]) -> bool:
        """Create monitoring alarm"""
        pass


class NotificationService(ABC):
    """Interface for notification services"""
    
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Send email notification"""
        pass
    
    @abstractmethod
    async def send_push_notification(self, user_id: str, title: str, message: str) -> bool:
        """Send push notification"""
        pass


class FileStorageService(ABC):
    """Interface for file storage services"""
    
    @abstractmethod
    async def upload_file(self, file_path: str, content: bytes, content_type: str = None) -> str:
        """Upload file and return URL"""
        pass
    
    @abstractmethod
    async def download_file(self, file_path: str) -> bytes:
        """Download file content"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        pass


class AnalyticsService(ABC):
    """Interface for analytics and reporting services"""
    
    @abstractmethod
    async def track_user_event(self, user_id: str, event: str, properties: Dict[str, Any]) -> bool:
        """Track user behavior event"""
        pass
    
    @abstractmethod
    async def generate_report(self, report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics report"""
        pass
    
    @abstractmethod
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user behavior insights"""
        pass
