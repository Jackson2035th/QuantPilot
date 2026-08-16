from datetime import date
from types import SimpleNamespace

import pandas as pd

from backtests.services.engine import _extract_equity_curve, run_backtest
from backtests.services.schema import ParsedStrategy


def test_run_ma_crossover_returns_equity_curve_and_metrics():
    index = pd.date_range("2024-01-01", periods=80, freq="D")
    prices = []
    for number in range(80):
        prices.append(100 + number * 0.5)

    frame = pd.DataFrame(
        {
            "open": prices,
            "high": [price + 1 for price in prices],
            "low": [price - 1 for price in prices],
            "close": prices,
            "volume": [1000000] * 80,
        },
        index=index,
    )
    frame.index.name = "date"

    strategy = ParsedStrategy(
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 20),
        initial_cash=10000,
        parameters={"short_window": 5, "long_window": 20},
        buy_rule="Buy when short MA crosses above long MA.",
        sell_rule="Sell when short MA crosses below long MA.",
    )

    output = run_backtest(strategy, frame)

    assert len(output.equity_curve) > 10
    assert isinstance(output.trades, list)
    assert "total_return" in output.metrics
    assert "max_drawdown" in output.metrics


def test_equity_curve_keeps_zero_account_value_but_drops_nan():
    result = SimpleNamespace(
        observers=SimpleNamespace(
            equityobserver=SimpleNamespace(
                lines=SimpleNamespace(
                    value=SimpleNamespace(array=[10000.0, 0.0, float("nan")])
                )
            )
        )
    )
    price_data = pd.DataFrame(
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    )

    curve = _extract_equity_curve(result, price_data)

    assert curve == [
        {"date": "2024-01-01", "value": 10000.0},
        {"date": "2024-01-02", "value": 0.0},
    ]
