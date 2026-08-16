from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import requests

from backtests.services.llm import (
    BACKTEST_DISCLAIMER,
    DeepSeekProvider,
    LLMProviderError,
    validate_backtest_explanation,
)


def _strategy():
    return SimpleNamespace(
        name="AAPL momentum check",
        ticker="AAPL",
        strategy_type="rsi",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 6, 30),
    )


def _result():
    return SimpleNamespace(
        total_return=0.12,
        annualized_return=0.24,
        sharpe_ratio=1.3,
        max_drawdown=-0.08,
        win_rate=0.58,
        number_of_trades=14,
        profit_factor=1.7,
        equity_curve_json=[{"date": "2024-01-01", "value": 10000}],
    )


def test_explain_backtest_sends_only_safe_summary_fields():
    provider = DeepSeekProvider("secret-key", "https://api.example.test", "deepseek-chat")
    response = Mock(status_code=200)
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        "- Return was positive over the selected period.\n"
                        "- Drawdown remained limited in this historical sample.\n"
                        "- Trade frequency was modest for this strategy."
                    )
                }
            }
        ]
    }

    with patch("backtests.services.llm.requests.post", return_value=response) as post:
        explanation = provider.explain_backtest(_strategy(), _result())

    assert explanation == (
        "- Return was positive over the selected period.\n"
        "- Drawdown remained limited in this historical sample.\n"
        "- Trade frequency was modest for this strategy.\n\n"
        f"{BACKTEST_DISCLAIMER}"
    )
    payload = post.call_args.kwargs["json"]
    assert payload["temperature"] == 0
    request_text = payload["messages"][1]["content"]
    assert "AAPL momentum check" in request_text
    assert "AAPL" in request_text
    assert "equity_curve_json" not in request_text
    assert "10000" not in request_text
    assert "secret-key" not in request_text
    assert "Do not include a heading, introduction, conclusion, or disclaimer." in (
        payload["messages"][0]["content"]
    )


def test_explain_backtest_does_not_duplicate_the_disclaimer():
    provider = DeepSeekProvider("key", "https://api.example.test", "deepseek-chat")
    response = Mock(status_code=200)
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        "- Historical return was positive.\n"
                        "- Drawdown was limited in this sample.\n"
                        "- Trade frequency was low.\n"
                        f"{BACKTEST_DISCLAIMER}"
                    ),
                }
            }
        ]
    }

    with patch("backtests.services.llm.requests.post", return_value=response):
        explanation = provider.explain_backtest(_strategy(), _result())

    assert explanation.count(BACKTEST_DISCLAIMER) == 1
    assert explanation.endswith(BACKTEST_DISCLAIMER)


@pytest.mark.parametrize("content", [None, "", "   "])
def test_explain_backtest_rejects_missing_or_empty_responses(content):
    provider = DeepSeekProvider("key", "https://api.example.test", "deepseek-chat")
    response = Mock(status_code=200)
    response.json.return_value = {"choices": [{"message": {"content": content}}]}

    with patch("backtests.services.llm.requests.post", return_value=response):
        with pytest.raises(LLMProviderError, match="explanation"):
            provider.explain_backtest(_strategy(), _result())


def test_explain_backtest_wraps_network_errors():
    provider = DeepSeekProvider("key", "https://api.example.test", "deepseek-chat")

    with patch(
        "backtests.services.llm.requests.post",
        side_effect=requests.Timeout("Timed out"),
    ):
        with pytest.raises(LLMProviderError, match="request failed"):
            provider.explain_backtest(_strategy(), _result())


@pytest.mark.parametrize(
    "content",
    [
        "You should buy this stock because the return was positive.",
        "We recommend increasing your investment.",
        "This strategy offers a guaranteed profit.",
        "The stock will rise next month.",
    ],
)
def test_explanation_rejects_advice_guarantees_and_predictions(content):
    with pytest.raises(LLMProviderError, match="advice or a prediction"):
        validate_backtest_explanation(content)


def test_explanation_rejects_an_overlong_response():
    with pytest.raises(LLMProviderError, match="too long"):
        validate_backtest_explanation("x" * 901)


def test_explanation_rejects_unstructured_or_excessive_points():
    with pytest.raises(LLMProviderError, match="concise bullet list"):
        validate_backtest_explanation("A prose explanation without bullet points.")

    with pytest.raises(LLMProviderError, match="concise bullet list"):
        validate_backtest_explanation(
            "\n".join(f"- Point {index}" for index in range(5))
        )


def test_parse_strategy_prompt_lists_required_rsi_parameter_names(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"strategy_type": "rsi", "ticker": "TSLA", '
                        '"start_date": "2020-01-01", "end_date": "2024-12-31", '
                        '"initial_cash": 10000, "parameters": '
                        '{"rsi_period": 14, "oversold_threshold": 30, '
                        '"overbought_threshold": 70}, "buy_rule": "Buy below 30", '
                        '"sell_rule": "Sell above 70"}'
                    )
                }
            }
        ]
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("backtests.services.llm.requests.post", post)
    provider = DeepSeekProvider("key", "https://api.example.test", "deepseek-chat")

    provider.parse_strategy(
        "Backtest TSLA using RSI(14). Buy below 30 and sell above 70 from "
        "2020-01-01 to 2024-12-31 with $10,000."
    )

    system_prompt = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "rsi_period, oversold_threshold, overbought_threshold" in system_prompt
    assert "Never choose or invent omitted values" in system_prompt
    assert '"status":"incomplete"' in system_prompt


def test_parse_strategy_wraps_network_errors():
    provider = DeepSeekProvider("key", "https://api.example.test", "deepseek-chat")

    with patch(
        "backtests.services.llm.requests.post",
        side_effect=requests.Timeout("Timed out"),
    ):
        with pytest.raises(LLMProviderError, match="request failed"):
            provider.parse_strategy("Backtest an AAPL moving average crossover strategy.")


def test_parse_strategy_rejects_a_malformed_provider_response():
    provider = DeepSeekProvider("key", "https://api.example.test", "deepseek-chat")
    response = Mock(status_code=200)
    response.json.return_value = {"choices": []}

    with patch("backtests.services.llm.requests.post", return_value=response):
        with pytest.raises(LLMProviderError, match="did not contain a strategy"):
            provider.parse_strategy("Backtest an AAPL moving average crossover strategy.")
