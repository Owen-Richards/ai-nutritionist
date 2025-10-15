import os
import hmac
import hashlib
import json
import pytest

@pytest.fixture(autouse=True)
def _wa_env(monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "whatsapp_cloud")
    monkeypatch.setenv("WHATSAPP_CLOUD_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_CLOUD_APP_SECRET", "appsecret")
    monkeypatch.setenv("WHATSAPP_CLOUD_WEBHOOK_VALIDATION", "true")
    yield


def test_wa_cloud_send(monkeypatch):
    from services.messaging_service.src.application.sms import WhatsAppCloudPlatform
    class Resp:
        status_code = 200
        text = "ok"

    def _fake_post(url, headers=None, data=None, timeout=None):
        body = json.loads(data)
        assert "messages" in url
        assert headers["Authorization"].startswith("Bearer ")
        assert body["messaging_product"] == "whatsapp"
        assert body["to"] == "1234567890"
        return Resp()

    import requests
    monkeypatch.setattr(requests, "post", _fake_post)

    p = WhatsAppCloudPlatform()
    assert p.send_message("+1234567890", "hello") is True


def test_wa_cloud_validation():
    from services.messaging_service.src.application.sms import WhatsAppCloudPlatform
    p = WhatsAppCloudPlatform()
    body = json.dumps({"object":"whatsapp_business_account","entry":[]})
    sig = hmac.new(b"appsecret", body.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={sig}"}
    assert p.validate_webhook(headers, body) is True


def test_wa_cloud_parse():
    from services.messaging_service.src.application.sms import WhatsAppCloudPlatform
    p = WhatsAppCloudPlatform()
    payload = {
        "object":"whatsapp_business_account",
        "entry":[{"changes":[{"value":{"messages":[{"from":"15551234567","text":{"body":"hi"}}]}}]}]
    }
    norm = p.parse_incoming_message(payload)
    assert norm["platform"] == "whatsapp"
    assert norm["message"] == "hi"
