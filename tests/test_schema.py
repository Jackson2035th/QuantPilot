from datetime import date

import pytest

from backtests.services.schema import (
    ParsedStrategy,
    StrategyValidationError,
    parse_strategy_payload,
    strategy_to_dict,
)
from backtests.services.llm import (
    DeepSeekProvider,
    LLMProviderError,
    parse_llm_json_response,
)


def valid_payload(**overrides):
    payload = {
        "strategy_type": "ma_crossover",
        "ticker": "aapl",
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "initial_cash": 10000,
        "parameters": {"short_window": 20, "long_window": 50},
        "buy_rule": "Buy when the short moving average crosses above the long moving average.",
        "sell_rule": "Sell when the short moving average crosses below the long moving average.",
    }
    payload.update(overrides)
    return payload


def test_parse_valid_ma_crossover_payload():
    parsed = parse_strategy_payload(valid_payload())

    assert parsed == ParsedStrategy(
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date=date(2020, 1, 1),
        end_date=date(2024, 12, 31),
        initial_cash=10000.0,
        parameters={"short_window": 20, "long_window": 50},
        buy_rule="Buy when the short moving average crosses above the long moving average.",
        sell_rule="Sell when the short moving average crosses below the long moving average.",
    )


def test_parse_valid_rsi_payload():
    parsed = parse_strategy_payload(
        valid_payload(
            strategy_type="rsi",
            parameters={
                "rsi_period": 14,
                "oversold_threshold": 30,
                "overbought_threshold": 70,
            },
        )
    )

    assert parsed.strategy_type == "rsi"
    assert parsed.parameters == {
        "rsi_period": 14,
        "oversold_threshold": 30,
        "overbought_threshold": 70,
    }


def test_parse_valid_macd_payload():
    parsed = parse_strategy_payload(
        valid_payload(
            strategy_type="macd",
            parameters={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
            },
        )
    )

    assert parsed.strategy_type == "macd"
    assert parsed.parameters == {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
    }


def test_strategy_to_dict_serializes_dates():
    parsed = parse_strategy_payload(valid_payload())

    data = strategy_to_dict(parsed)

    assert data["start_date"] == "2020-01-01"
    assert data["end_date"] == "2024-12-31"
    assert data["ticker"] == "AAPL"


def test_rejects_missing_required_fields():
    fields = [
        "strategy_type",
        "ticker",
        "start_date",
        "end_date",
        "initial_cash",
        "parameters",
        "buy_rule",
        "sell_rule",
    ]

    for field in fields:
        payload = valid_payload()
        payload.pop(field)

        with pytest.raises(
            StrategyValidationError, match=f"Missing required field: {field}"
        ):
            parse_strategy_payload(payload)


def test_rejects_unsupported_strategy_type():
    with pytest.raises(StrategyValidationError, match="Unsupported strategy type"):
        parse_strategy_payload(valid_payload(strategy_type="bollinger"))


def test_rejects_blank_ticker():
    with pytest.raises(StrategyValidationError, match="Ticker must be a US stock symbol"):
        parse_strategy_payload(valid_payload(ticker=""))


def test_rejects_numeric_ticker():
    with pytest.raises(StrategyValidationError, match="Ticker must be a US stock symbol"):
        parse_strategy_payload(valid_payload(ticker="1234"))


def test_rejects_ticker_with_symbol():
    with pytest.raises(StrategyValidationError, match="Ticker must be a US stock symbol"):
        parse_strategy_payload(valid_payload(ticker="AAPL!"))


def test_rejects_ticker_that_is_too_long():
    with pytest.raises(StrategyValidationError, match="Ticker must be a US stock symbol"):
        parse_strategy_payload(valid_payload(ticker="TOO-LONG-SYMBOL"))


def test_rejects_start_date_not_before_end_date():
    with pytest.raises(StrategyValidationError, match="start_date must be before end_date"):
        parse_strategy_payload(
            valid_payload(start_date="2024-12-31", end_date="2024-12-31")
        )


def test_rejects_future_start_date():
    with pytest.raises(StrategyValidationError, match="Dates cannot be in the future"):
        parse_strategy_payload(
            valid_payload(start_date="2999-01-01", end_date="2999-12-31")
        )


def test_rejects_future_end_date():
    with pytest.raises(StrategyValidationError, match="Dates cannot be in the future"):
        parse_strategy_payload(valid_payload(end_date="2999-12-31"))


def test_rejects_non_positive_initial_cash():
    with pytest.raises(StrategyValidationError, match="initial_cash must be positive"):
        parse_strategy_payload(valid_payload(initial_cash=0))


def test_rejects_parameters_that_are_not_an_object():
    with pytest.raises(StrategyValidationError, match="parameters must be an object"):
        parse_strategy_payload(valid_payload(parameters=[]))


def test_rejects_invalid_ma_window_order():
    with pytest.raises(
        StrategyValidationError, match="short_window must be less than long_window"
    ):
        parse_strategy_payload(
            valid_payload(parameters={"short_window": 50, "long_window": 20})
        )


def test_rejects_invalid_rsi_threshold_order():
    with pytest.raises(
        StrategyValidationError,
        match="oversold_threshold must be less than overbought_threshold",
    ):
        parse_strategy_payload(
            valid_payload(
                strategy_type="rsi",
                parameters={
                    "rsi_period": 14,
                    "oversold_threshold": 70,
                    "overbought_threshold": 30,
                },
            )
        )


def test_rejects_invalid_macd_period_order():
    with pytest.raises(
        StrategyValidationError, match="fast_period must be less than slow_period"
    ):
        parse_strategy_payload(
            valid_payload(
                strategy_type="macd",
                parameters={
                    "fast_period": 26,
                    "slow_period": 12,
                    "signal_period": 9,
                },
            )
        )


def test_parse_llm_json_response_accepts_plain_json():
    payload = parse_llm_json_response(
        '{"strategy_type": "ma_crossover", "ticker": "AAPL"}'
    )

    assert payload["ticker"] == "AAPL"


def test_parse_llm_json_response_accepts_fenced_json():
    payload = parse_llm_json_response(
        '```json\n{"strategy_type": "rsi", "ticker": "MSFT"}\n```'
    )

    assert payload["strategy_type"] == "rsi"


def test_parse_llm_json_response_rejects_invalid_json():
    with pytest.raises(LLMProviderError, match="LLM response was not valid JSON"):
        parse_llm_json_response("not json")


def test_deepseek_provider_rejects_missing_api_key():
    provider = DeepSeekProvider(api_key="", base_url="https://example.com", model="test")

    with pytest.raises(LLMProviderError, match="DEEPSEEK_API_KEY is not configured"):
        provider.parse_strategy("Buy Apple with moving averages")


def test_deepseek_provider_returns_parsed_strategy(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"strategy_type": "ma_crossover", '
                                '"ticker": "AAPL", '
                                '"start_date": "2020-01-01", '
                                '"end_date": "2024-12-31", '
                                '"initial_cash": 10000, '
                                '"parameters": {"short_window": 20, "long_window": 50}, '
                                '"buy_rule": "Buy", '
                                '"sell_rule": "Sell"}'
                            )
                        }
                    }
                ]
            }

    def fake_post(url, headers, json, timeout):
        assert url == "https://example.com/chat/completions"
        assert headers["Authorization"] == "Bearer secret"
        assert json["model"] == "test-model"
        assert timeout == 30
        return FakeResponse()

    import backtests.services.llm as llm

    monkeypatch.setattr(llm.requests, "post", fake_post)
    provider = DeepSeekProvider(
        api_key="secret", base_url="https://example.com", model="test-model"
    )

    parsed = provider.parse_strategy("Buy Apple with moving averages")

    assert parsed.strategy_type == "ma_crossover"
    assert parsed.ticker == "AAPL"
