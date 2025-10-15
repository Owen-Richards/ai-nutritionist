"""
Test Automation Utilities

Provides utilities for Selenium automation, API testing, 
message simulation, and database verification.
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import aiohttp
import boto3
from unittest.mock import Mock, AsyncMock


class SeleniumAutomation:
    """Advanced Selenium automation utilities"""
    
    def __init__(self, browser: str = "chrome", headless: bool = True):
        self.browser = browser
        self.headless = headless
        self.driver: Optional[webdriver.Remote] = None
        self.wait: Optional[WebDriverWait] = None
        self.action_chains: Optional[ActionChains] = None
        
    def setup_driver(self) -> webdriver.Remote:
        """Setup and configure web driver"""
        if self.browser.lower() == "chrome":
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # Performance optimizations
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            
            self.driver = webdriver.Chrome(options=options)
            
        elif self.browser.lower() == "firefox":
            options = FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")
            
            self.driver = webdriver.Firefox(options=options)
            
        else:
            raise ValueError(f"Unsupported browser: {self.browser}")
        
        self.wait = WebDriverWait(self.driver, 30)
        self.action_chains = ActionChains(self.driver)
        
        return self.driver
    
    def navigate_to(self, url: str) -> None:
        """Navigate to URL with error handling"""
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        self.driver.get(url)
        self.wait_for_page_load()
    
    def wait_for_page_load(self, timeout: int = 30) -> None:
        """Wait for page to fully load"""
        self.wait.until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    
    def find_element_safe(self, locator: tuple, timeout: int = 10) -> Optional[Any]:
        """Find element with timeout, return None if not found"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.presence_of_element_located(locator))
        except:
            return None
    
    def find_clickable_element(self, locator: tuple, timeout: int = 10) -> Optional[Any]:
        """Find clickable element with timeout"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.element_to_be_clickable(locator))
        except:
            return None
    
    def click_element_safe(self, locator: tuple, timeout: int = 10) -> bool:
        """Click element safely with error handling"""
        element = self.find_clickable_element(locator, timeout)
        if element:
            try:
                element.click()
                return True
            except:
                # Try JavaScript click as fallback
                self.driver.execute_script("arguments[0].click();", element)
                return True
        return False
    
    def type_text_safe(self, locator: tuple, text: str, clear_first: bool = True) -> bool:
        """Type text into element safely"""
        element = self.find_element_safe(locator)
        if element:
            try:
                if clear_first:
                    element.clear()
                element.send_keys(text)
                return True
            except:
                pass
        return False
    
    def scroll_to_element(self, locator: tuple) -> bool:
        """Scroll element into view"""
        element = self.find_element_safe(locator)
        if element:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)  # Wait for scroll animation
            return True
        return False
    
    def hover_over_element(self, locator: tuple) -> bool:
        """Hover over element"""
        element = self.find_element_safe(locator)
        if element and self.action_chains:
            self.action_chains.move_to_element(element).perform()
            return True
        return False
    
    def take_screenshot(self, filename: str) -> str:
        """Take screenshot and return file path"""
        if not self.driver:
            return ""
        
        timestamp = int(time.time())
        filepath = f"tests/e2e/screenshots/{filename}_{timestamp}.png"
        self.driver.save_screenshot(filepath)
        return filepath
    
    def get_element_text(self, locator: tuple) -> str:
        """Get element text safely"""
        element = self.find_element_safe(locator)
        return element.text if element else ""
    
    def get_element_attribute(self, locator: tuple, attribute: str) -> str:
        """Get element attribute safely"""
        element = self.find_element_safe(locator)
        return element.get_attribute(attribute) if element else ""
    
    def wait_for_text_in_element(self, locator: tuple, text: str, timeout: int = 10) -> bool:
        """Wait for specific text to appear in element"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.text_to_be_present_in_element(locator, text))
            return True
        except:
            return False
    
    def wait_for_element_to_disappear(self, locator: tuple, timeout: int = 10) -> bool:
        """Wait for element to disappear"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until_not(EC.presence_of_element_located(locator))
            return True
        except:
            return False
    
    def switch_to_iframe(self, iframe_locator: tuple) -> bool:
        """Switch to iframe"""
        iframe = self.find_element_safe(iframe_locator)
        if iframe:
            self.driver.switch_to.frame(iframe)
            return True
        return False
    
    def switch_to_default_content(self) -> None:
        """Switch back to main content"""
        if self.driver:
            self.driver.switch_to.default_content()
    
    def handle_alert(self, accept: bool = True) -> str:
        """Handle JavaScript alert"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            if accept:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        except:
            return ""
    
    def execute_javascript(self, script: str, *args) -> Any:
        """Execute JavaScript"""
        if self.driver:
            return self.driver.execute_script(script, *args)
        return None
    
    def close_driver(self) -> None:
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None


class APIAutomation:
    """Advanced API testing automation utilities"""
    
    def __init__(self, base_url: str, default_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {'Content-Type': 'application/json'}
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_log: List[Dict[str, Any]] = []
        
    async def create_session(self) -> aiohttp.ClientSession:
        """Create HTTP session"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.default_headers
        )
        
        return self.session
    
    async def close_session(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with comprehensive error handling"""
        
        if not self.session:
            await self.create_session()
        
        url = f"{self.base_url}{endpoint}"
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        request_start = time.time()
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data,
                data=data,
                timeout=aiohttp.ClientTimeout(total=timeout) if timeout else None
            ) as response:
                
                response_time = time.time() - request_start
                
                # Read response body
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    response_body = await response.json()
                else:
                    response_body = await response.text()
                
                # Log request/response
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'method': method,
                    'url': url,
                    'status': response.status,
                    'response_time': response_time,
                    'request_headers': request_headers,
                    'response_headers': dict(response.headers),
                    'request_body': json_data or data,
                    'response_body': response_body[:1000] if isinstance(response_body, str) else response_body  # Truncate long responses
                }
                self.request_log.append(log_entry)
                
                return {
                    'status': response.status,
                    'headers': dict(response.headers),
                    'body': response_body,
                    'response_time': response_time,
                    'success': 200 <= response.status < 300
                }
                
        except asyncio.TimeoutError:
            return {
                'status': 408,
                'error': 'Request timeout',
                'response_time': time.time() - request_start
            }
        except Exception as e:
            return {
                'status': 500,
                'error': str(e),
                'response_time': time.time() - request_start
            }
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        return await self.make_request('GET', endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST request"""
        return await self.make_request('POST', endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT request"""
        return await self.make_request('PUT', endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request"""
        return await self.make_request('DELETE', endpoint, **kwargs)
    
    async def patch(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PATCH request"""
        return await self.make_request('PATCH', endpoint, **kwargs)
    
    def get_request_log(self, filter_status: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get request log with optional status filter"""
        if filter_status:
            return [log for log in self.request_log if log['status'] == filter_status]
        return self.request_log.copy()
    
    def clear_request_log(self) -> None:
        """Clear request log"""
        self.request_log.clear()
    
    def calculate_api_metrics(self) -> Dict[str, Any]:
        """Calculate API performance metrics"""
        if not self.request_log:
            return {}
        
        response_times = [log['response_time'] for log in self.request_log]
        status_codes = [log['status'] for log in self.request_log]
        
        return {
            'total_requests': len(self.request_log),
            'avg_response_time': sum(response_times) / len(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'success_rate': len([s for s in status_codes if 200 <= s < 300]) / len(status_codes),
            'error_rate': len([s for s in status_codes if s >= 400]) / len(status_codes),
            'status_distribution': {str(s): status_codes.count(s) for s in set(status_codes)}
        }


class MessageSimulationAutomation:
    """Advanced message simulation for different channels"""
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.message_queue: List[Dict[str, Any]] = []
        self.webhook_responses: List[Dict[str, Any]] = []
        self.api_automation = None
        
    async def setup(self, api_base_url: str) -> None:
        """Setup message simulation"""
        self.api_automation = APIAutomation(api_base_url)
        await self.api_automation.create_session()
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.api_automation:
            await self.api_automation.close_session()
    
    async def simulate_whatsapp_message(
        self,
        from_number: str,
        message: str,
        message_type: str = "text",
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Simulate WhatsApp message"""
        
        message_data = {
            'From': f"whatsapp:{from_number}",
            'To': 'whatsapp:+1234567890',  # Bot number
            'Body': message,
            'MessageSid': f"SM{int(time.time())}{hash(message) % 1000:03d}",
            'AccountSid': 'test_account_sid',
            'MessagingServiceSid': 'test_messaging_service_sid',
            'NumMedia': '1' if media_url else '0',
            'MediaUrl0': media_url if media_url else '',
            'MediaContentType0': 'image/jpeg' if media_url else '',
            'SmsStatus': 'received',
            'ApiVersion': '2010-04-01'
        }
        
        # Send to webhook
        response = await self._send_webhook(
            endpoint='/webhook/whatsapp',
            data=message_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        return {
            'message_id': message_data['MessageSid'],
            'status': 'sent',
            'response': response
        }
    
    async def simulate_sms_message(
        self,
        from_number: str,
        message: str
    ) -> Dict[str, Any]:
        """Simulate SMS message"""
        
        message_data = {
            'From': from_number,
            'To': '+1234567890',  # Bot number
            'Body': message,
            'MessageSid': f"SM{int(time.time())}{hash(message) % 1000:03d}",
            'AccountSid': 'test_account_sid',
            'SmsStatus': 'received',
            'ApiVersion': '2010-04-01'
        }
        
        # Send to webhook
        response = await self._send_webhook(
            endpoint='/webhook/sms',
            data=message_data,
            content_type='application/x-www-form-urlencoded'
        )
        
        return {
            'message_id': message_data['MessageSid'],
            'status': 'sent',
            'response': response
        }
    
    async def simulate_imessage_message(
        self,
        from_email: str,
        message: str
    ) -> Dict[str, Any]:
        """Simulate iMessage"""
        
        message_data = {
            'from': from_email,
            'to': 'bot@ai-nutritionist.com',
            'body': message,
            'message_id': f"IM{int(time.time())}{hash(message) % 1000:03d}",
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to webhook
        response = await self._send_webhook(
            endpoint='/webhook/imessage',
            data=message_data,
            content_type='application/json'
        )
        
        return {
            'message_id': message_data['message_id'],
            'status': 'sent',
            'response': response
        }
    
    async def _send_webhook(
        self,
        endpoint: str,
        data: Dict[str, Any],
        content_type: str = 'application/json'
    ) -> Dict[str, Any]:
        """Send webhook request"""
        
        if not self.api_automation:
            raise RuntimeError("Message simulation not initialized")
        
        if content_type == 'application/json':
            response = await self.api_automation.post(endpoint, json_data=data)
        else:
            # Form-encoded data
            import urllib.parse
            form_data = urllib.parse.urlencode(data)
            response = await self.api_automation.post(
                endpoint,
                data=form_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
        
        self.webhook_responses.append(response)
        return response
    
    async def wait_for_outbound_message(
        self,
        timeout: int = 30,
        channel: str = "any"
    ) -> Optional[Dict[str, Any]]:
        """Wait for outbound message from bot"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for outbound messages via API
            response = await self.api_automation.get('/messages/outbound/recent')
            
            if response['success'] and response['body']:
                messages = response['body'].get('messages', [])
                
                # Filter by channel if specified
                if channel != "any":
                    messages = [m for m in messages if m.get('channel') == channel]
                
                if messages:
                    return messages[0]
            
            await asyncio.sleep(1)  # Wait before checking again
        
        return None
    
    def get_webhook_log(self) -> List[Dict[str, Any]]:
        """Get webhook request log"""
        return self.webhook_responses.copy()
    
    def clear_webhook_log(self) -> None:
        """Clear webhook log"""
        self.webhook_responses.clear()


class DatabaseVerificationAutomation:
    """Database verification utilities for E2E tests"""
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.dynamodb = None
        self.rds_client = None
        
    def setup_aws_clients(self) -> None:
        """Setup AWS clients for database access"""
        if self.environment == "test":
            # Use local DynamoDB for testing
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url='http://localhost:8000',  # Local DynamoDB
                region_name='us-east-1',
                aws_access_key_id='test',
                aws_secret_access_key='test'
            )
        else:
            self.dynamodb = boto3.resource('dynamodb')
            self.rds_client = boto3.client('rds')
    
    async def verify_user_created(self, user_id: str) -> bool:
        """Verify user was created in database"""
        try:
            table = self.dynamodb.Table('Users')
            response = table.get_item(Key={'user_id': user_id})
            return 'Item' in response
        except Exception:
            return False
    
    async def verify_meal_logged(self, user_id: str, meal_data: Dict[str, Any]) -> bool:
        """Verify meal was logged correctly"""
        try:
            table = self.dynamodb.Table('MealLogs')
            
            # Query meals for user
            response = table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            
            meals = response.get('Items', [])
            
            # Check if meal with matching data exists
            for meal in meals:
                if all(meal.get(key) == value for key, value in meal_data.items()):
                    return True
            
            return False
        except Exception:
            return False
    
    async def verify_subscription_updated(self, user_id: str, tier: str) -> bool:
        """Verify subscription tier was updated"""
        try:
            table = self.dynamodb.Table('Users')
            response = table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                user = response['Item']
                return user.get('subscription_tier') == tier
            
            return False
        except Exception:
            return False
    
    async def verify_family_member_added(self, user_id: str, member_name: str) -> bool:
        """Verify family member was added"""
        try:
            table = self.dynamodb.Table('FamilyMembers')
            
            response = table.query(
                KeyConditionExpression='primary_user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            
            members = response.get('Items', [])
            return any(member.get('name') == member_name for member in members)
        except Exception:
            return False
    
    async def verify_health_data_synced(self, user_id: str, data_type: str) -> bool:
        """Verify health data was synced"""
        try:
            table = self.dynamodb.Table('HealthData')
            
            response = table.query(
                KeyConditionExpression='user_id = :user_id AND data_type = :data_type',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':data_type': data_type
                }
            )
            
            return len(response.get('Items', [])) > 0
        except Exception:
            return False
    
    async def cleanup_test_data(self, user_ids: List[str]) -> None:
        """Clean up test data from database"""
        tables = ['Users', 'MealLogs', 'FamilyMembers', 'HealthData', 'Subscriptions']
        
        for table_name in tables:
            try:
                table = self.dynamodb.Table(table_name)
                
                for user_id in user_ids:
                    # Delete all items for this user
                    response = table.query(
                        KeyConditionExpression='user_id = :user_id',
                        ExpressionAttributeValues={':user_id': user_id}
                    )
                    
                    for item in response.get('Items', []):
                        table.delete_item(Key={'user_id': user_id, 'sort_key': item.get('sort_key', '')})
                        
            except Exception:
                pass  # Continue with cleanup even if some deletions fail
    
    async def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete user data for verification"""
        try:
            table = self.dynamodb.Table('Users')
            response = table.get_item(Key={'user_id': user_id})
            return response.get('Item')
        except Exception:
            return None
    
    async def get_meal_history(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get user's meal history"""
        try:
            table = self.dynamodb.Table('MealLogs')
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            response = table.query(
                KeyConditionExpression='user_id = :user_id AND log_date BETWEEN :start_date AND :end_date',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':start_date': start_date.isoformat(),
                    ':end_date': end_date.isoformat()
                }
            )
            
            return response.get('Items', [])
        except Exception:
            return []
