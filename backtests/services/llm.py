import json
import re
from dataclasses import dataclass

import requests

from .schema import ParsedStrategy, parse_strategy_payload


class LLMProviderError(RuntimeError):
    pass


BACKTEST_DISCLAIMER = "Historical results do not guarantee future performance."
MAX_EXPLANATION_BODY_LENGTH = 900
MIN_EXPLANATION_POINTS = 3
MAX_EXPLANATION_POINTS = 4
UNSAFE_EXPLANATION_PATTERNS = [
    # These regular expressions catch common forms of advice, promises, or predictions.
    re.compile(
        r"\byou\s+(?:should|must|need to)\s+(?:buy|sell|invest|trade|hold)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:i|we)\s+(?:recommend|advise)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:buy|sell)\s+(?:this|the)\s+(?:stock|asset|security)\s+(?:now|today)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bguaranteed\s+(?:return|profit|gain)\b", re.IGNORECASE),
    re.compile(r"\b(?:risk[- ]free|cannot lose)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:the\s+)?(?:price|stock|market|shares?)\s+(?:will|is going to)\s+"
        r"(?:rise|fall|increase|decrease|go up|go down|outperform|underperform)\b",
        re.IGNORECASE,
    ),
]


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
                        {"role": "system", "content": _system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    # Deterministic output makes schema validation and user review predictable.
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
            raw_text = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("LLM response did not contain a strategy") from exc

        if not isinstance(raw_text, str) or not raw_text.strip():
            raise LLMProviderError("LLM response did not contain a strategy")
        # A successful HTTP response is still untrusted until its JSON and trading
        # rules pass the same schema used for browser submissions.
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

        # Keep advice, predictions, and malformed output out of the dashboard.
        return validate_backtest_explanation(content)


def validate_backtest_explanation(content) -> str:
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError("LLM response did not contain an explanation")

    text = content.strip()
    # Remove a provider-written copy so the application adds the disclaimer once.
    text = re.sub(
        re.escape(BACKTEST_DISCLAIMER),
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    if not text:
        raise LLMProviderError("LLM response did not contain an explanation")
    if len(text) > MAX_EXPLANATION_BODY_LENGTH:
        raise LLMProviderError("LLM explanation was too long")

    # Reject advice, promises, and predictions before showing the text to the user.
    for pattern in UNSAFE_EXPLANATION_PATTERNS:
        if pattern.search(text):
            raise LLMProviderError("LLM explanation contained advice or a prediction")

    points = [line.strip() for line in text.splitlines() if line.strip()]
    if not MIN_EXPLANATION_POINTS <= len(points) <= MAX_EXPLANATION_POINTS:
        raise LLMProviderError("LLM explanation was not a concise bullet list")
    if any(not point.startswith("- ") for point in points):
        raise LLMProviderError("LLM explanation was not a concise bullet list")
    if any(len(point) > 260 for point in points):
        raise LLMProviderError("LLM explanation was not a concise bullet list")

    body = "\n".join(points)
    return f"{body}\n\n{BACKTEST_DISCLAIMER}"


def parse_llm_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    # Some providers wrap JSON in a Markdown fence despite the prompt instruction.
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
        "Required user-provided information is an explicitly named stock (ticker or company), "
        "one supported strategy, every numeric strategy parameter, a buy rule, a sell rule, "
        "two dates, and initial cash. Never choose or invent omitted values and never use "
        "default strategy settings. You may resolve an explicitly named company to its ticker, "
        "but you must never choose a stock that the user did not name. "
        "If any required information is missing or ambiguous, return only "
        '{"status":"incomplete","missing_fields":["field_name"]}. '
        "Each missing_fields value must be one of ticker, strategy_type, parameters, buy_rule, "
        "sell_rule, start_date, end_date, or initial_cash. "
        "Do not include guessed strategy fields in an incomplete response. "
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
        "non-technical investor. Return exactly 3 or 4 concise plain-text bullet "
        "points, each beginning with '- ' and no more than 35 words. Do not include "
        "a heading, introduction, conclusion, or disclaimer. Describe only the "
        "supplied historical metrics. Cover performance, drawdown or risk, and "
        "trading behaviour or a limitation. Do not give financial advice, "
        "predictions, or trading recommendations."
    )


def _backtest_explanation_request(strategy, result) -> str:
    # Aggregate metrics are enough for the explanation and avoid sending daily prices.
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
