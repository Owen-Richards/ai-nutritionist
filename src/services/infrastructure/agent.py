"""Reasoning agent that orchestrates tool usage via Amazon Bedrock."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """
You are an orchestration agent for the AI Nutritionist.
Decide whether to respond directly or call a tool.

Available tools:
- meal_plan: create or refresh a weekly meal plan.
- nutrition_question: answer a nutrition or health related question by calling the nutrition service.
- subscription_info: explain pricing tiers and upgrade paths.
- grocery_list: help with grocery list requests.
- small_talk: friendly conversational response (no tool call required).

Output strictly as compact JSON with keys:
{
  "action": "respond" | "tool_call" | "fallback",
  "confidence": 0.0-1.0,
  "assistant_response": optional string when action == "respond",
  "tool": optional tool name when action == "tool_call",
  "parameters": optional object with tool arguments
}

User message: "{message}"
Platform: {platform}
Primary goal: {primary_goal}
Recent preferences: {preferences}

Respond with JSON only.
"""


class ReasoningAgent:
    """Thin wrapper around Bedrock text generation for reasoning."""

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.getenv(
            "BEDROCK_REASONING_MODEL", "amazon.titan-text-express-v1"
        )
        self.client = boto3.client("bedrock-runtime")

    def decide(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured decision for the given message and context."""
        prompt = _PROMPT_TEMPLATE.format(
            message=user_message,
            platform=context.get("platform", "unknown"),
            primary_goal=context.get("primary_goal", "unspecified"),
            preferences=json.dumps(context.get("preferences", {}))[:512],
        )

        body = json.dumps(
            {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 512,
                    "temperature": 0.3,
                    "topP": 0.9,
                },
            }
        )

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
            output = payload.get("results", [{}])[0].get("outputText", "")
            decision = self._safe_parse_json(output)
            if decision:
                return decision
        except ClientError as exc:
            logger.error("Bedrock agent invocation failed: %s", exc)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Unexpected error invoking reasoning agent: %s", exc)

        return {"action": "fallback", "confidence": 0.0}

    @staticmethod
    def _safe_parse_json(raw_text: str) -> Dict[str, Any]:
        raw_text = raw_text.strip()
        if not raw_text:
            return {}
        # Attempt to isolate JSON object if model wrapped it in prose
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start == -1 or end <= start:
            return {}
        candidate = raw_text[start:end]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            logger.debug("Could not parse agent output as JSON: %s", raw_text)
        return {}
