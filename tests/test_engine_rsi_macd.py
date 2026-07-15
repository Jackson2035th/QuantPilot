from datetime import date

import pandas as pd
import pytest

from backtests.services.engine import run_backtest
from backtests.services.schema import ParsedStrategy


def sample_price_data():
    index = pd.date_range("2024-01-01", periods=120, freq="D")
    prices = []
    for number in range(120):
        price = 100 + ((number % 30) - 15) * 0.8 + number * 0.1
        prices.append(price)

    frame = pd.DataFrame(
        {
            "open": prices,
            "high": [price + 1 for price in prices],
            "low": [price - 1 for price in prices],
            "close": prices,
            "volume": [1000000] * 120,
        },
        index=index,
    )
    frame.index.name = "date"
    return frame


@pytest.mark.parametrize(
    "strategy_type,parameters",
    [
        (
            "rsi",
            {
                "rsi_period": 14,
                "oversold_threshold": 30,
                "overbought_threshold": 70,
            },
        ),
        (
            "macd",
            {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
            },
        ),
    ],
)
def test_run_rsi_and_macd_return_metrics(strategy_type, parameters):
    strategy = ParsedStrategy(
        strategy_type=strategy_type,
        ticker="AAPL",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 4, 30),
        initial_cash=10000,
        parameters=parameters,
        buy_rule="Buy rule",
        sell_rule="Sell rule",
    )

    output = run_backtest(strategy, sample_price_data())

    assert len(output.equity_curve) > 10
    assert "sharpe_ratio" in output.metrics
