from backtests.services.metrics import calculate_metrics


def test_calculate_metrics_for_profitable_equity_curve():
    equity_curve = [
        {"date": "2024-01-01", "value": 10000.0},
        {"date": "2024-01-02", "value": 10100.0},
        {"date": "2024-01-03", "value": 9900.0},
        {"date": "2024-01-04", "value": 11000.0},
    ]
    trades = [{"pnl": 100.0}, {"pnl": -50.0}, {"pnl": 200.0}]

    metrics = calculate_metrics(equity_curve, trades, initial_cash=10000.0)

    assert round(metrics["total_return"], 4) == 0.1
    assert metrics["number_of_trades"] == 3
    assert round(metrics["win_rate"], 4) == 0.6667
    assert metrics["profit_factor"] == 6.0
    assert metrics["max_drawdown"] < 0


def test_calculate_metrics_handles_no_trades():
    equity_curve = [
        {"date": "2024-01-01", "value": 10000.0},
        {"date": "2024-01-02", "value": 10000.0},
    ]

    metrics = calculate_metrics(equity_curve, [], initial_cash=10000.0)

    assert metrics["number_of_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["profit_factor"] == 0.0
