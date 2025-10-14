import os
import hmac
import hashlib
import base64
import json
import types

import pytest

# Basic smoke tests for Twilio messaging provider

@pytest.fixture(autouse=True)
def _twilio_env(monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "twilio")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "auth_token")
    monkeypatch.setenv("TWILIO_SMS_FROM", "+12025550123")
    monkeypatch.setenv("TWILIO_WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.setenv("TWILIO_WEBHOOK_VALIDATION", "true")
    yield


def test_twilio_send_success(monkeypatch):
    from services.messaging_service.src.application.sms import TwilioMessagingPlatform
    class Resp:
        status_code = 201
        text = "ok"

    def _fake_post(url, data=None, auth=None, timeout=None):
        assert "Messages.json" in url
        assert data["From"] == "+12025550123"
        assert data["To"] == "+1234567890"
        assert data["Body"] == "hello"
        return Resp()

    import requests
    monkeypatch.setattr(requests, "post", _fake_post)

    p = TwilioMessagingPlatform("sms")
    assert p.send_message("+1234567890", "hello") is True


def test_twilio_webhook_validation(monkeypatch):
    from services.messaging_service.src.application.sms import TwilioMessagingPlatform
    p = TwilioMessagingPlatform("sms")
    payload = {"From": "+123", "Body": "hi"}
    body = "From=%2B123&Body=hi"  # urlencoded order matches sorted params
    concat = os.environ["TWILIO_WEBHOOK_URL"] + "BodyhiFrom+123"
    expected = base64.b64encode(hmac.new(b"auth_token", concat.encode("utf-8"), hashlib.sha1).digest()).decode("utf-8")

    headers = {"X-Twilio-Signature": expected}
    assert p.validate_webhook(headers, body) is True


def test_twilio_parse_incoming_message():
    from services.messaging_service.src.application.sms import TwilioMessagingPlatform
    p = TwilioMessagingPlatform("sms")
    payload = {"From": "+1234567890", "Body": "hello"}
    norm = p.parse_incoming_message(payload)
    assert norm["platform"] == "sms"
    assert norm["user_id"].endswith("1234567890")
    assert norm["message"] == "hello"
