from __future__ import annotations

import json
import logging
from typing import Any

from src.common.auth.credentials import get_access_token
from src.common.config.settings import get_settings, load_model_profile
from src.common.models.contracts import Classification

logger = logging.getLogger(__name__)


class AzureOpenAIAdapter:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._profile = load_model_profile()

    def classify_invoice(
        self,
        system_prompt: str,
        invoice_text: str,
        tool_definition: dict,
    ) -> Classification:
        deployment = self._profile.get("classification_model", self._settings.AOAI_DEPLOYMENT)
        token = get_access_token()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": invoice_text},
        ]

        tool = {
            "type": "function",
            "function": tool_definition,
        }

        import httpx

        url = (
            f"{self._settings.AOAI_ENDPOINT}openai/deployments/{deployment}"
            f"/chat/completions?api-version={self._settings.AOAI_API_VERSION}"
        )

        body: dict[str, Any] = {
            "messages": messages,
            "tools": [tool],
            "tool_choice": {"type": "function", "function": {"name": tool_definition["name"]}},
            "temperature": self._profile.get("temperature", 0.1),
        }
        max_tokens = self._profile.get("max_completion_tokens")
        if max_tokens:
            body["max_completion_tokens"] = int(max_tokens)

        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        tool_calls = choice.get("message", {}).get("tool_calls", [])
        if not tool_calls:
            logger.warning("No tool call returned from classification")
            return Classification()

        args = json.loads(tool_calls[0]["function"]["arguments"])
        return Classification(
            spend_category=args.get("spend_category", ""),
            subcategory=args.get("subcategory", ""),
            is_likely_duplicate=args.get("is_likely_duplicate", False),
            anomaly_flags=args.get("anomaly_flags", []),
            confidence=args.get("confidence", 0.0),
            reasoning=args.get("reasoning", ""),
        )

    def embed(self, text: str) -> list[float]:
        token = get_access_token()
        deployment = self._settings.AOAI_DEPLOYMENT_EMBEDDING

        import httpx

        url = (
            f"{self._settings.AOAI_ENDPOINT}openai/deployments/{deployment}"
            f"/embeddings?api-version={self._settings.AOAI_API_VERSION}"
        )

        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"input": text, "model": deployment},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
