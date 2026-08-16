import pytest

from backtests.forms import ConfirmedStrategyForm, StrategyPromptForm
from backtests.guide import GUIDE_EXAMPLES


VALID_PROMPT = (
    "Backtest MSFT with MACD 12, 26, 9. Buy on a bullish crossover and sell on "
    "a bearish crossover from 2020-01-01 to 2024-12-31 with $10,000."
)


def test_strategy_prompt_accepts_an_explicit_complete_strategy():
    form = StrategyPromptForm({"prompt": VALID_PROMPT})

    assert form.is_valid(), form.errors


@pytest.mark.parametrize("example", GUIDE_EXAMPLES, ids=lambda item: item["title"])
def test_every_guide_example_is_a_complete_valid_prompt(example):
    form = StrategyPromptForm({"prompt": example["prompt"]})

    assert form.is_valid(), form.errors


@pytest.mark.parametrize(
    ("prompt", "message"),
    [
        (
            "BACKTEST USING RSI(14). BUY below 30 and SELL above 70 from "
            "2020-01-01 to 2024-12-31 with $10,000.",
            "Add a US stock ticker or company name.",
        ),
        (
            "Backtest with MACD 12, 26, 9. Buy on a bullish crossover and sell on a "
            "bearish crossover from 2020-01-01 to 2024-12-31 with $10,000.",
            "Add a US stock ticker or company name.",
        ),
        (
            "Backtest MSFT from 2020-01-01 to 2024-12-31 with $10,000.",
            "Add one supported strategy",
        ),
        (
            "Backtest MSFT using RSI. Buy when oversold and sell when overbought from "
            "2020-01-01 to 2024-12-31 with $10,000.",
            "Add all strategy parameters",
        ),
        (
            "Backtest MSFT using RSI(14), below 30 and above 70 from 2020-01-01 to "
            "2024-12-31 with $10,000.",
            "Describe both the buy rule and the sell rule.",
        ),
    ],
)
def test_strategy_prompt_rejects_missing_information(prompt, message):
    form = StrategyPromptForm({"prompt": prompt})

    assert not form.is_valid()
    assert message in form.errors["prompt"][0]


@pytest.mark.parametrize(
    "invalid_date",
    ["20240-01-01", "2024-13-01", "2024-02-30", "2024-1-01"],
)
def test_confirmed_strategy_form_rejects_non_strict_or_invalid_dates(invalid_date):
    form = ConfirmedStrategyForm(
        {
            "name": "MSFT MACD",
            "strategy_type": "macd",
            "ticker": "MSFT",
            "start_date": invalid_date,
            "end_date": "2024-12-31",
            "initial_cash": "10000",
            "fast_period": "12",
            "slow_period": "26",
            "signal_period": "9",
            "buy_rule": "Buy on a bullish crossover.",
            "sell_rule": "Sell on a bearish crossover.",
        }
    )

    assert not form.is_valid()
    assert "four-digit year" in form.errors["start_date"][0]


def test_confirmed_strategy_form_rejects_end_date_before_start_date():
    form = ConfirmedStrategyForm(
        {
            "name": "MSFT MACD",
            "strategy_type": "macd",
            "ticker": "MSFT",
            "start_date": "2024-12-31",
            "end_date": "2024-01-01",
            "initial_cash": "10000",
            "fast_period": "12",
            "slow_period": "26",
            "signal_period": "9",
            "buy_rule": "Buy on a bullish crossover.",
            "sell_rule": "Sell on a bearish crossover.",
        }
    )

    assert not form.is_valid()
    assert "after the start date" in form.errors["end_date"][0]


@pytest.mark.parametrize("invalid_date", ["2024-13-01", "2024-02-30"])
def test_strategy_prompt_rejects_an_invalid_calendar_date(invalid_date):
    prompt = VALID_PROMPT.replace("2020-01-01", invalid_date)
    form = StrategyPromptForm({"prompt": prompt})

    assert not form.is_valid()
    assert "month from 01 to 12, and a valid day" in form.errors["prompt"][0]


def test_confirmed_strategy_form_builds_rsi_parameters_from_structured_fields():
    form = ConfirmedStrategyForm(
        {
            "name": "TSLA RSI",
            "strategy_type": "rsi",
            "ticker": "TSLA",
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "initial_cash": "10000",
            "rsi_period": "14",
            "oversold_threshold": "30",
            "overbought_threshold": "70",
            "buy_rule": "Buy below 30.",
            "sell_rule": "Sell above 70.",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["parameters"] == {
        "rsi_period": 14,
        "oversold_threshold": 30,
        "overbought_threshold": 70,
    }
