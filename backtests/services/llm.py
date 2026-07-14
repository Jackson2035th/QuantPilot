import json
import re
from dataclasses import dataclass

import requests

from .schema import ParsedStrategy, parse_strategy_payload


class LLMProviderError(RuntimeError):
    pass


class LLMProvider:
    def parse_strategy(self, prompt: str) -> ParsedStrategy:
        raise NotImplementedError


@dataclass
class DeepSeekProvider(LLMProvider):
    api_key: str
    base_url: str
    model: str

    def parse_strategy(self, prompt: str) -> ParsedStrategy:
        if not self.api_key:
            raise LLMProviderError("DEEPSEEK_API_KEY is not configured")

        response = requests.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=30,
        )

        if response.status_code >= 400:
            raise LLMProviderError(
                f"LLM provider returned HTTP {response.status_code}"
            )

        data = response.json()
        raw_text = data["choices"][0]["message"]["content"]
        payload = parse_llm_json_response(raw_text)
        return parse_strategy_payload(payload)


def parse_llm_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM response was not valid JSON") from exc

    if not isinstance(payload, dict):
        raise LLMProviderError("LLM response JSON must be an object")

    return payload


def _system_prompt() -> str:
    return (
        "You convert natural language trading strategies into strict JSON only. "
        "Supported strategy_type values are ma_crossover, rsi, and macd. "
        "Return keys: strategy_type, ticker, start_date, end_date, initial_cash, "
        "parameters, buy_rule, sell_rule. Do not return markdown or executable code."
    )
