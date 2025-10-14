from services.messaging.templates import MessageTemplatesService


def _decision(journey: str) -> dict:
    return {
        "journey": journey,
        "primary_message": "Plan ready.",
        "cta_label": "View plan",
        "deep_link": "https://ai.health/plans/today?utm_source=sms&utm_campaign=today&locale=en-US",
        "metadata": {"context": "sms | en-US | UTC | Alex | balanced/none | adherence | Day 1 | 1 | 10"},
    }


def test_sms_renderer_includes_stop_phrase() -> None:
    service = MessageTemplatesService()
    rendered = service.render_next_best_action(_decision("today"), channel="sms", locale="en-US", timezone="UTC")
    assert "Reply STOP to opt out" in rendered["text"]
    assert rendered["cta"]["label"] == "View plan"
    assert "utm_source" in rendered["cta"]["deep_link"]


def test_whatsapp_renderer_uses_bullets() -> None:
    service = MessageTemplatesService()
    decision = _decision("groceries")
    decision["cta_label"] = "Ouvrir les courses"
    decision["deep_link"] = "https://ai.health/plans/today?utm_source=whatsapp&utm_campaign=groceries&locale=fr-FR"
    rendered = service.render_next_best_action(decision, channel="whatsapp", locale="fr-FR", timezone="Europe/Paris")
    assert "•" in rendered["text"]
    assert rendered["cta"]["label"] == "Ouvrir les courses"
    assert rendered["metadata"]["render"]["rtl"] is False
