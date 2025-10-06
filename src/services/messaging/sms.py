"""Messaging primitives with pluggable providers (Twilio, AWS End User Messaging, others).

This module provides multi-provider messaging capabilities for SMS and WhatsApp delivery. 
The AWS End User Messaging service (which replaced Amazon Pinpoint communication channels in Q3 2024) 
provides SMS delivery capabilities, while Twilio and WhatsApp Cloud API provide alternative delivery methods.
"""

from __future__ import annotations

import json
import logging
import hashlib
import hmac
import os
import random
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import boto3
import requests
from botocore.exceptions import ClientError
from urllib.parse import parse_qs
import base64

logger = logging.getLogger(__name__)

# Best-effort usage recorder to DynamoDB usage table for cost/limits visibility
def _record_usage(phone: str, provider: str, channel: str) -> None:
    try:
        table_name = os.getenv("USAGE_TABLE_NAME")
        if not table_name:
            # Fallback to environment naming if present
            env = os.getenv("ENVIRONMENT", "dev").lower()
            table_name = f"ai-nutritionist-usage-{env}"
        if not table_name:
            return
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(table_name)
        from datetime import datetime
        now = datetime.utcnow()
        month = now.strftime("%Y-%m")
        day_key = now.strftime("%Y-%m-%d")
        inc_key = f"{provider.lower()}_{channel.lower()}_sent"
        table.update_item(
            Key={"user_phone": phone, "month": month},
            UpdateExpression=(
                "ADD messages_sent :one, #ik :one "
                "SET last_message_at = :ts, "
                "#daily = if_not_exists(#daily, :empty_map), "
                "#daily.#day = if_not_exists(#daily.#day, :empty_map), "
                "#daily.#day.#provider = if_not_exists(#daily.#day.#provider, :zero) + :one"
            ),
            ExpressionAttributeValues={
                ":one": 1,
                ":ts": now.isoformat(),
                ":empty_map": {},
                ":zero": 0
            },
            ExpressionAttributeNames={
                "#ik": inc_key,
                "#daily": "daily_counts",
                "#day": day_key,
                "#provider": f"{provider.lower()}_{channel.lower()}"
            },
        )
    except Exception:
        # Non-fatal; avoid impacting send path
        pass


class MessagePlatform(ABC):
    """Abstract messaging platform contract."""

    @abstractmethod
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Deliver a message to *to*. Returns ``True`` on success."""

    @abstractmethod
    def validate_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        """Validate an incoming webhook payload."""

    @abstractmethod
    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Turn provider specific payloads into a normalized structure."""

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the canonical platform name (e.g. ``sms``)."""


class AWSEndUserMessagingPlatform(MessagePlatform):
    """AWS End User Messaging backed SMS delivery.
    
    Note: Amazon Pinpoint communication channels (SMS, MMS, push, WhatsApp, and text to voice
    messaging capabilities) were renamed in Q3 2024 as AWS End User Messaging, and will continue
    to serve developer needs for message delivery with customers.
    """

    def __init__(self, channel: str) -> None:
        if channel not in {"sms"}:
            raise ValueError(f"Unsupported AWS End User Messaging channel: {channel}")

        self.channel = channel
        self.aws_sms_client = boto3.client("pinpoint-sms-voice-v2")
        self.ssm = boto3.client("ssm")

        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.configuration_set = (
            os.getenv("AWS_SMS_CONFIGURATION_SET")
            or os.getenv("SMS_CONFIG_SET")
        )
        self.sms_origination = os.getenv("AWS_SMS_ORIGINATION_IDENTITY")

    # ------------------------------------------------------------------
    # MessagePlatform interface
    # ------------------------------------------------------------------
    def send_message(
        self,
        to: str,
        message: str,
        media_url: Optional[str] = None,
    ) -> bool:
        destination = self._normalize_number(to)

        try:
            return self._send_sms(destination, message)
        except ClientError as exc:
            logger.error("AWS End User Messaging %s error: %s", self.channel, exc)
            return False
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Unexpected messaging error (%s): %s", self.channel, exc)
            return False

    def validate_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        # AWS validates signatures via SNS; surface level checks happen higher up.
        return True

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        origin = self._normalize_number(
            payload.get("originationNumber")
            or payload.get("from")
            or payload.get("phoneNumber")
            or payload.get("sender")
            or ""
        )
        message_body = (
            payload.get("messageBody")
            or payload.get("body")
            or payload.get("text")
            or payload.get("message")
        )

        if not origin or message_body is None:
            return None

        return {
            "platform": self.channel,
            "user_id": origin,
            "phone_number": origin,
            "message": message_body,
            "raw_data": payload,
        }

    def get_platform_name(self) -> str:
        return self.channel

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _send_sms(self, destination: str, message: str) -> bool:
        origination = self._resolve_sms_origination()
        if not origination:
            logger.error("No SMS origination identity configured")
            return False

        kwargs: Dict[str, Any] = {
            "DestinationPhoneNumber": destination,
            "MessageBody": message,
            "OriginationIdentity": origination,
            "MessageType": "TRANSACTIONAL",
        }
        if self.configuration_set:
            kwargs["ConfigurationSetName"] = self.configuration_set

        response = self.aws_sms_client.send_text_message(**kwargs)
        logger.info("Sent SMS message %s", response.get("MessageId"))
        return True

    def _resolve_sms_origination(self) -> Optional[str]:
        if self.sms_origination:
            return self.sms_origination
        return self._fetch_parameter(f"/{self.environment}/messaging/origination-number")

    def _fetch_parameter(self, name: str) -> Optional[str]:
        try:
            response = self.ssm.get_parameter(Name=name, WithDecryption=True)
            return response["Parameter"]["Value"]
        except self.ssm.exceptions.ParameterNotFound:
            logger.debug("Parameter %s not found", name)
            return None
        except Exception as exc:
            logger.warning("Could not load parameter %s: %s", name, exc)
            return None

    @staticmethod
    def _normalize_number(value: str) -> str:
        if not value:
            return value
        value = value.strip()
        if not value.startswith("+") and value.isdigit():
            value = "+" + value
        return value


class TelegramPlatform(MessagePlatform):
    """Telegram messaging via bot token."""

    def __init__(self) -> None:
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        if not self.api_url:
            logger.error("Telegram bot token is not configured")
            return False

        try:
            if media_url:
                url = f"{self.api_url}/sendPhoto"
                data = {
                    "chat_id": to,
                    "photo": media_url,
                    "caption": message,
                    "parse_mode": "Markdown",
                }
            else:
                url = f"{self.api_url}/sendMessage"
                data = {
                    "chat_id": to,
                    "text": message,
                    "parse_mode": "Markdown",
                }

            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram message sent to %s", to)
                return True

            logger.error("Telegram API error: %s", response.text)
            return False
        except Exception as exc:
            logger.error("Error sending Telegram message: %s", exc)
            return False

    def validate_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        if not self.webhook_secret:
            return True
        auth_header = headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not auth_header:
            return False
        return hmac.compare_digest(auth_header, self.webhook_secret)

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        message = payload.get("message", {})
        user = message.get("from", {})
        text = message.get("text")
        if text is None:
            return None
        return {
            "platform": "telegram",
            "user_id": str(user.get("id", "")),
            "message": text,
            "phone_number": str(user.get("id", "")),
            "raw_data": payload,
        }

    def get_platform_name(self) -> str:
        return "telegram"


class MessengerPlatform(MessagePlatform):
    """Facebook Messenger via the Graph API."""

    def __init__(self) -> None:
        self.access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.api_url = "https://graph.facebook.com/v18.0/me/messages"

    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        if not self.access_token:
            logger.error("Facebook access token is not configured")
            return False

        try:
            headers = {"Content-Type": "application/json"}
            if media_url:
                data = {
                    "recipient": {"id": to},
                    "message": {
                        "attachment": {
                            "type": "image",
                            "payload": {"url": media_url},
                        }
                    },
                    "access_token": self.access_token,
                }
            else:
                data = {
                    "recipient": {"id": to},
                    "message": {"text": message},
                    "access_token": self.access_token,
                }

            response = requests.post(self.api_url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("Messenger message sent to %s", to)
                return True

            logger.error("Messenger API error: %s", response.text)
            return False
        except Exception as exc:
            logger.error("Error sending Messenger message: %s", exc)
            return False

    def validate_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        if not self.app_secret:
            return True
        signature = headers.get("X-Hub-Signature")
        if not signature:
            return False
        digest = hmac.new(self.app_secret.encode(), body.encode(), hashlib.sha1).hexdigest()
        return hmac.compare_digest(signature, f"sha1={digest}")

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            entry = payload.get("entry", [])[0]
            messaging = entry.get("messaging", [])[0]
            sender_id = messaging.get("sender", {}).get("id")
            text = messaging.get("message", {}).get("text")
            if not sender_id or text is None:
                return None
            return {
                "platform": "messenger",
                "user_id": sender_id,
                "message": text,
                "phone_number": sender_id,
                "raw_data": payload,
            }
        except Exception as exc:
            logger.error("Error parsing Messenger message: %s", exc)
            return None

    def get_platform_name(self) -> str:
        return "messenger"

class TwilioMessagingPlatform(MessagePlatform):
    """Twilio-backed SMS/WhatsApp delivery and webhook parsing.

    Environment variables:
    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_SMS_FROM (E.164, e.g. +12025550123)
    - TWILIO_WHATSAPP_FROM (e.g. whatsapp:+14155238886)
    - TWILIO_WEBHOOK_URL (optional, required for strict signature validation)
    - TWILIO_WEBHOOK_VALIDATION ("true" to enforce signature check)
    """

    API_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(self, channel: str) -> None:
        if channel not in {"sms", "whatsapp"}:
            raise ValueError(f"Unsupported Twilio channel: {channel}")
        self.channel = channel
        # Prefer SSM/Secrets Manager via environment config if available
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.sms_from = os.getenv("TWILIO_SMS_FROM")
        self.whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
        try:
            from src.config.environment import config as env_config
            self.account_sid = self.account_sid or env_config.get_secret("twilio_account_sid", None)
            self.auth_token = self.auth_token or env_config.get_secret("twilio_auth_token", None)
            self.sms_from = self.sms_from or env_config.get_parameter("twilio_sms_from", None)
            self.whatsapp_from = self.whatsapp_from or env_config.get_parameter("twilio_whatsapp_from", None)
        except Exception:
            pass
        self.webhook_url = os.getenv("TWILIO_WEBHOOK_URL")
        self.enforce_validation = str(os.getenv("TWILIO_WEBHOOK_VALIDATION", "true")).lower() == "true"

        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio credentials not configured (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)")

    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        destination = self._normalize_number(to)
        from_number = self._resolve_from()
        if not from_number:
            logger.error("Twilio 'from' sender is not configured for %s", self.channel)
            return False

        url = f"{self.API_BASE}/Accounts/{self.account_sid}/Messages.json"
        data: Dict[str, Any] = {"To": destination, "From": from_number, "Body": message}
        if media_url:
            data["MediaUrl"] = media_url

        try:
            resp = requests.post(url, data=data, auth=(self.account_sid, self.auth_token), timeout=10)
            if 200 <= resp.status_code < 300:
                logger.info("Twilio message accepted (%s) to %s", self.channel, destination)
                self._emit_cw_metric("MessageSent", 1)
                _record_usage(destination, "Twilio", self.channel)
                return True
            logger.error("Twilio error %s: %s", resp.status_code, resp.text)
            self._emit_cw_metric("MessageFailed", 1)
            return False
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Twilio send error: %s", exc)
            self._emit_cw_metric("MessageFailed", 1)
            return False

    def validate_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        # Twilio sends X-Twilio-Signature; validate if configured
        try:
            signature = headers.get("X-Twilio-Signature") or headers.get("x-twilio-signature")
            if not signature:
                return not self.enforce_validation
            if not self.webhook_url:
                return not self.enforce_validation

            # Twilio signature is Base64(HMAC-SHA1(AuthToken, URL + sortedParams))
            params = self._parse_body_to_params(body)
            concatenated = self.webhook_url + "".join(k + v for k, v in sorted(params.items()))
            digest = hmac.new(self.auth_token.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha1).digest()
            expected = base64.b64encode(digest).decode("utf-8")
            return hmac.compare_digest(signature, expected)
        except Exception as exc:
            logger.warning("Twilio webhook validation error: %s", exc)
            return not self.enforce_validation

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Twilio webhooks provide From/Body; For WhatsApp From starts with 'whatsapp:'
        origin = payload.get("From") or payload.get("from")
        text = payload.get("Body") or payload.get("body")
        if not origin or text is None:
            return None

        phone = self._normalize_number(str(origin))
        platform = "whatsapp" if str(origin).lower().startswith("whatsapp:") else "sms"
        return {
            "platform": platform,
            "user_id": phone,
            "phone_number": phone,
            "message": str(text),
            "raw_data": payload,
        }

    def get_platform_name(self) -> str:
        return self.channel

    # Internal helpers
    def _resolve_from(self) -> Optional[str]:
        if self.channel == "whatsapp":
            return self.whatsapp_from
        return self.sms_from

    @staticmethod
    def _normalize_number(value: str) -> str:
        if not value:
            return value
        v = value.strip()
        if v.lower().startswith("whatsapp:"):
            v = v.split(":", 1)[1]
        if not v.startswith("+") and v.isdigit():
            v = "+" + v
        return v if not (str(value).lower().startswith("whatsapp:")) else f"whatsapp:{v}"

    @staticmethod
    def _parse_body_to_params(body: str) -> Dict[str, str]:
        try:
            parsed = {k: v[0] if isinstance(v, list) and v else "" for k, v in parse_qs(body or "").items()}
            if parsed:
                return parsed
            # Fallback to JSON if present
            obj = json.loads(body) if body else {}
            return {k: str(v) for k, v in obj.items()}
        except Exception:
            try:
                obj = json.loads(body) if body else {}
                return {k: str(v) for k, v in obj.items()}
            except Exception:
                return {}

    def _emit_cw_metric(self, metric_name: str, value: float) -> None:
        try:
            cw = boto3.client("cloudwatch")
            cw.put_metric_data(
                Namespace="AI-Nutritionist/Messaging",
                MetricData=[{
                    "MetricName": metric_name,
                    "Dimensions": [
                        {"Name": "Provider", "Value": "Twilio"},
                        {"Name": "Channel", "Value": self.channel}
                    ],
                    "Unit": "Count",
                    "Value": value
                }]
            )
        except Exception:
            pass

class WhatsAppCloudPlatform(MessagePlatform):
    """WhatsApp Cloud API (Meta) provider for WhatsApp messaging and webhooks.

    Env/SSM/Secrets:
    - WHATSAPP_CLOUD_ACCESS_TOKEN
    - WHATSAPP_CLOUD_PHONE_NUMBER_ID
    - WHATSAPP_CLOUD_APP_SECRET (for webhook signature verification)
    - WHATSAPP_CLOUD_WEBHOOK_VALIDATION (default true)
    - WHATSAPP_CLOUD_WEBHOOK_URL (optional for completeness)
    """

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self) -> None:
        self.access_token = os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID")
        self.app_secret = os.getenv("WHATSAPP_CLOUD_APP_SECRET")
        self.enforce_validation = str(os.getenv("WHATSAPP_CLOUD_WEBHOOK_VALIDATION", "true")).lower() == "true"
        try:
            from src.config.environment import config as env_config
            self.access_token = self.access_token or env_config.get_secret("whatsapp_cloud_access_token", None)
            self.phone_number_id = self.phone_number_id or env_config.get_parameter("whatsapp_cloud_phone_number_id", None)
            self.app_secret = self.app_secret or env_config.get_secret("whatsapp_cloud_app_secret", None)
        except Exception:
            pass
        if not self.access_token or not self.phone_number_id:
            raise ValueError("WhatsApp Cloud API credentials not configured")

    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        try:
            url = f"{self.API_BASE}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload: Dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": to.lstrip("+"),
                "type": "text",
                "text": {"body": message}
            }
            if media_url:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to.lstrip("+"),
                    "type": "image",
                    "image": {"link": media_url, "caption": message}
                }
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            if 200 <= resp.status_code < 300:
                logger.info("WhatsApp Cloud message accepted to %s", to)
                self._emit_cw_metric("MessageSent", 1)
                _record_usage("+" + to.lstrip("+"), "WhatsAppCloud", "whatsapp")
                return True
            logger.error("WhatsApp Cloud error %s: %s", resp.status_code, resp.text)
            self._emit_cw_metric("MessageFailed", 1)
            return False
        except Exception as exc:
            logger.error("WhatsApp Cloud send error: %s", exc)
            self._emit_cw_metric("MessageFailed", 1)
            return False

    def validate_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        try:
            signature = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256")
            if not signature:
                return not self.enforce_validation
            if not self.app_secret:
                return not self.enforce_validation
            expected = hmac.new(self.app_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, f"sha256={expected}")
        except Exception:
            return not self.enforce_validation

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            entries = payload.get("entry", [])
            if not entries:
                return None
            changes = entries[0].get("changes", [])
            if not changes:
                return None
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None
            msg = messages[0]
            origin = msg.get("from")  # phone number without +
            text = (msg.get("text") or {}).get("body")
            if not origin or text is None:
                return None
            phone = "+" + origin if not origin.startswith("+") else origin
            return {
                "platform": "whatsapp",
                "user_id": phone,
                "phone_number": phone,
                "message": text,
                "raw_data": payload,
            }
        except Exception as exc:
            logger.error("WhatsApp Cloud parse error: %s", exc)
            return None

    def get_platform_name(self) -> str:
        return "whatsapp"

    def _emit_cw_metric(self, metric_name: str, value: float) -> None:
        try:
            cw = boto3.client("cloudwatch")
            cw.put_metric_data(
                Namespace="AI-Nutritionist/Messaging",
                MetricData=[{
                    "MetricName": metric_name,
                    "Dimensions": [
                        {"Name": "Provider", "Value": "WhatsAppCloud"},
                        {"Name": "Channel", "Value": "whatsapp"}
                    ],
                    "Unit": "Count",
                    "Value": value
                }]
            )
        except Exception:
            pass


class UniversalMessagingService:
    """High level messaging facade used by the application."""

    def __init__(self) -> None:
        self.platforms: Dict[str, MessagePlatform] = {}

        provider = (os.getenv("MESSAGING_PROVIDER", "").strip().lower())

        # WhatsApp Cloud preferred if explicitly selected or credentials are set
        use_whatsapp_cloud = provider == "whatsapp_cloud" or (
            not provider and os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN") and os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID")
        )
        if use_whatsapp_cloud:
            # Only provides WhatsApp channel
            try:
                self.platforms["whatsapp"] = WhatsAppCloudPlatform()
            except Exception as exc:
                logger.warning("Could not initialise WhatsApp Cloud platform: %s", exc)

        # Twilio for SMS/WhatsApp unless WhatsApp already provided by Cloud API
        use_twilio = provider == "twilio" or (
            not provider and os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")
        )
        if use_twilio:
            for name in ("sms", "whatsapp"):
                # Don't overwrite whatsapp if already provided by WhatsAppCloud
                if name == "whatsapp" and "whatsapp" in self.platforms:
                    continue
                try:
                    self.platforms[name] = TwilioMessagingPlatform(name)
                except Exception as exc:
                    logger.warning("Could not initialise Twilio %s platform: %s", name, exc)

        # DEPRECATED: AWS End User Messaging SMS fallback (scheduled for removal Oct 30, 2026)
        # Only use if no other providers are available
        if not self.platforms:
            logger.warning("No primary messaging providers available, falling back to deprecated AWS End User Messaging")
            for name in ("sms", "whatsapp"):
                try:
                    self.platforms[name] = AWSEndUserMessagingPlatform(name)
                except Exception as exc:
                    logger.warning("Could not initialise AWS End User Messaging %s platform: %s", name, exc)

        if os.getenv("TELEGRAM_BOT_TOKEN"):
            try:
                self.platforms["telegram"] = TelegramPlatform()
            except Exception as exc:
                logger.warning("Could not initialise Telegram platform: %s", exc)

        if os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN"):
            try:
                self.platforms["messenger"] = MessengerPlatform()
            except Exception as exc:
                logger.warning("Could not initialise Messenger platform: %s", exc)

        logger.info("Initialised messaging platforms: %s", list(self.platforms.keys()))

    # ------------------------------------------------------------------
    # Outbound messaging helpers
    # ------------------------------------------------------------------
    def send_message(
        self,
        platform: str,
        to: str,
        message: str,
        media_url: Optional[str] = None,
    ) -> bool:
        handler = self.platforms.get(platform)
        if not handler:
            logger.error("Platform %s not available", platform)
            return False
        return handler.send_message(to, message, media_url)

    def send_to_all_user_platforms(
        self,
        user_id: str,
        message: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for name in ("whatsapp", "sms", "telegram", "messenger"):
            if name not in self.platforms:
                continue
            success = self.send_message(name, user_id, message, media_url)
            results[name] = success
            if success:
                break
        return results

    # ------------------------------------------------------------------
    # Inbound processing helpers
    # ------------------------------------------------------------------
    def verify_event_signature(self, event: Dict[str, Any], platform: str) -> bool:
        handler = self.platforms.get(platform)
        sns_record = self._extract_sns_record(event)
        if sns_record:
            cert_url = sns_record.get("SigningCertUrl") or sns_record.get("SigningCertURL")
            if not cert_url:
                logger.warning("SNS message missing SigningCertUrl")
                return False
            return "sns." in cert_url
        # Non-SNS webhook: delegate to provider-specific validation (e.g., Twilio)
        headers = event.get("headers") or {}
        body = event.get("body") or ""
        if isinstance(body, dict):
            body = json.dumps(body)
        return handler.validate_webhook(headers, body) if handler else False

    def detect_platform(self, event: Dict[str, Any]) -> Optional[str]:
        payload = self._extract_event_payload(event)
        if not payload:
            return None

        # WhatsApp Cloud webhook (Meta Graph)
        if isinstance(payload, dict) and payload.get("object") == "whatsapp_business_account":
            if "whatsapp" in self.platforms:
                return "whatsapp"

        channel = str(
            payload.get("channelType")
            or payload.get("ChannelType")
            or payload.get("channel")
            or ""
        ).lower()
        if channel == "whatsapp" and "whatsapp" in self.platforms:
            return "whatsapp"
        if channel == "sms" and "sms" in self.platforms:
            return "sms"

        origin = str(
            payload.get("originationNumber")
            or payload.get("from")
            or payload.get("From")
            or ""
        )
        if origin.startswith("whatsapp") and "whatsapp" in self.platforms:
            return "whatsapp"
        if "sms" in self.platforms:
            return "sms"
        return None

    def extract_message_data(
        self, event: Dict[str, Any], platform: str
    ) -> Optional[Dict[str, Any]]:
        payload = self._extract_event_payload(event)
        if not payload:
            return None

        handler = self.platforms.get(platform)
        if not handler:
            return None

        normalized = handler.parse_incoming_message(payload)
        if normalized:
            normalized["raw_event"] = event
        return normalized

    # ------------------------------------------------------------------
    # UX helpers
    # ------------------------------------------------------------------
    def format_friendly_message(self, message: str, platform: str = "whatsapp") -> str:
        message = message.strip()
        if platform == "whatsapp":
            message = message.replace("**", "*")
        if not re.match(r"^(hi|hello|hey)", message, flags=re.IGNORECASE):
            greetings = [
                "Hey! ",
                "Hi there! ",
                "Hello! ",
                ""
            ]
            message = random.choice(greetings) + message
        return message

    def create_contact_experience(
        self, user_message: str, user_profile: Dict[str, Any]
    ) -> str:
        lowered = user_message.lower()
        name = user_profile.get("name", "friend")
        if any(token in lowered for token in ["hi", "hello", "hey", "morning", "evening"]):
            responses = [
                f"Hey {name}! How can I help with nutrition today?",
                f"Hi {name}! Ready to work on your meal plan?",
                f"Hello {name}! Need ideas for your next meal?",
            ]
            return random.choice(responses)
        return "I'm right here if you need meal ideas, goal tracking, or nutrition tips!"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _extract_event_payload(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(event, dict):
            return None

        sns_record = self._extract_sns_record(event)
        if sns_record:
            message = sns_record.get("Message")
            return self._safe_load_json(message)

        body = event.get("body")
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        if isinstance(body, str):
            # Try JSON first
            as_json = self._safe_load_json(body)
            if as_json is not None:
                return as_json
            # Handle form-encoded payloads (e.g., Twilio webhooks)
            content_type = headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or ("twilio" in (headers.get("user-agent") or "").lower()):
                try:
                    parsed = parse_qs(body, keep_blank_values=True)
                    return {k: v[0] if isinstance(v, list) and v else "" for k, v in parsed.items()}
                except Exception:
                    logger.debug("Unable to parse form-encoded body")
            return None
        if isinstance(body, dict):
            return body

        detail = event.get("detail")
        if isinstance(detail, dict):
            return detail

        return None

    @staticmethod
    def _extract_sns_record(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        records = event.get("Records") if isinstance(event, dict) else None
        if not records:
            return None
        record = records[0]
        return record.get("Sns") or record.get("SNS")

    @staticmethod
    def _safe_load_json(raw: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("Unable to decode JSON payload: %s", raw)
            return None


class ConsolidatedMessagingService(UniversalMessagingService):
    """Extended facade with nutrition specific helpers."""

    def send_nutrition_message(
        self,
        to: str,
        template: str,
        platform: str = "whatsapp",
        **kwargs: Any,
    ) -> bool:
        message = template.format(**kwargs)
        friendly = self.format_friendly_message(message, platform)
        return self.send_message(platform, to, friendly)


