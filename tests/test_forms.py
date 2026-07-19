from backtests.forms import ConfirmedStrategyForm


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
