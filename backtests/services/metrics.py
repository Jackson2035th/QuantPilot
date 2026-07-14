import math

import pandas as pd


def calculate_metrics(
    equity_curve: list[dict], trades: list[dict], initial_cash: float
) -> dict:
    values = pd.Series([point["value"] for point in equity_curve], dtype="float64")
    returns = values.pct_change().dropna()

    final_value = float(values.iloc[-1])
    total_return = (final_value - initial_cash) / initial_cash

    periods = max(len(values) - 1, 1)
    annualized_return = (final_value / initial_cash) ** (252 / periods) - 1

    running_max = values.cummax()
    drawdowns = values / running_max - 1
    max_drawdown = float(drawdowns.min())

    winning_trades = []
    losing_trades = []
    for trade in trades:
        pnl = float(trade.get("pnl", 0))
        if pnl > 0:
            winning_trades.append(trade)
        elif pnl < 0:
            losing_trades.append(trade)

    number_of_trades = len(trades)
    if number_of_trades:
        win_rate = len(winning_trades) / number_of_trades
    else:
        win_rate = 0.0

    if len(returns) > 1 and returns.std():
        volatility = float(returns.std() * math.sqrt(252))
        sharpe_ratio = float((returns.mean() / returns.std()) * math.sqrt(252))
    else:
        volatility = 0.0
        sharpe_ratio = 0.0

    gross_profit = 0.0
    for trade in winning_trades:
        gross_profit += float(trade.get("pnl", 0))

    gross_loss = 0.0
    for trade in losing_trades:
        gross_loss += abs(float(trade.get("pnl", 0)))

    if gross_loss:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = 0.0

    return {
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "max_drawdown": max_drawdown,
        "number_of_trades": number_of_trades,
        "win_rate": float(win_rate),
        "sharpe_ratio": sharpe_ratio,
        "volatility": volatility,
        "profit_factor": float(profit_factor),
    }
