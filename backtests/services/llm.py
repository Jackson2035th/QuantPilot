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
                # A zero temperature asks for a more consistent response to the same strategy prompt.
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

    def explain_backtest(self, strategy, result) -> str:
        if not self.api_key:
            raise LLMProviderError("DEEPSEEK_API_KEY is not configured")

        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": _backtest_explanation_system_prompt()},
                        {
                            "role": "user",
                            "content": _backtest_explanation_request(strategy, result),
                        },
                    ],
                    "temperature": 0,
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            raise LLMProviderError("LLM provider request failed") from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"LLM provider returned HTTP {response.status_code}"
            )

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("LLM response did not contain an explanation") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("LLM response did not contain an explanation")
        return content.strip()


def parse_llm_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    # The model may still wrap JSON in a Markdown code block, so remove that wrapper first.
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
        "parameters, buy_rule, sell_rule. "
        "For ma_crossover, parameters must contain short_window and long_window. "
        "For rsi, parameters must contain rsi_period, oversold_threshold, overbought_threshold; "
        "map a buy-below value to oversold_threshold and a sell-above value to overbought_threshold. "
        "For macd, parameters must contain fast_period, slow_period, and signal_period. "
        "Do not return markdown or executable code."
    )


def _backtest_explanation_system_prompt() -> str:
    return (
        "Explain the supplied historical backtest summary in plain English for a "
        "non-technical investor. Describe only the supplied historical metrics. "
        "Do not give financial advice, predictions, or trading recommendations. "
        "End with this exact sentence: Historical results do not guarantee future performance."
    )


def _backtest_explanation_request(strategy, result) -> str:
    return (
        "Strategy summary:\n"
        f"- Name: {strategy.name}\n"
        f"- Ticker: {strategy.ticker}\n"
        f"- Strategy type: {strategy.strategy_type}\n"
        f"- Start date: {strategy.start_date.isoformat()}\n"
        f"- End date: {strategy.end_date.isoformat()}\n\n"
        "Historical aggregate metrics:\n"
        f"- Total return: {result.total_return:.2%}\n"
        f"- Annualized return: {result.annualized_return:.2%}\n"
        f"- Sharpe ratio: {result.sharpe_ratio:.2f}\n"
        f"- Maximum drawdown: {result.max_drawdown:.2%}\n"
        f"- Win rate: {result.win_rate:.2%}\n"
        f"- Number of trades: {result.number_of_trades}\n"
        f"- Profit factor: {result.profit_factor:.2f}"
    )
