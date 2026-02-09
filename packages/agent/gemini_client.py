"""Gemini API client using official google-generativeai SDK."""

from __future__ import annotations

import json
import os
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig


class GeminiClient:
    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
        self._model = None
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_text(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self._model:
            raise RuntimeError("Gemini API key not configured")

        # Combine for simple single-turn generation
        full_prompt = f"SYSTEM INSTRUCTION:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"

        config = GenerationConfig(temperature=temperature)
        
        try:
            response = self._model.generate_content(full_prompt, generation_config=config)
            if not response.parts:
                 raise RuntimeError("Gemini returned empty response")
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}") from e

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self._model:
            raise RuntimeError("Gemini API key not configured")

        full_prompt = f"SYSTEM INSTRUCTION:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"

        # efficient JSON mode
        config = GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )

        try:
            response = self._model.generate_content(full_prompt, generation_config=config)
            return json.loads(response.text)
        except Exception:
            # Fallback to manual extraction if native JSON mode fails or model mismatch
            text = self.generate_text(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.1)
            return _extract_json(text)


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        sliced = text[start : end + 1]
        payload = json.loads(sliced)
        if isinstance(payload, dict):
            return payload
    raise ValueError("Could not parse JSON payload from Gemini response")
