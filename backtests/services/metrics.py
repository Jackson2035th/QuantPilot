import math

import pandas as pd


def calculate_metrics(
    equity_curve: list[dict], trades: list[dict], initial_cash: float
) -> dict:
    values = pd.Series([point["value"] for point in equity_curve], dtype="float64")
    # Each curve point represents one trading day, so pct_change produces daily returns.
    returns = values.pct_change().dropna()

    final_value = float(values.iloc[-1])
    # Total return compares the final account value with the starting cash.
    total_return = (final_value - initial_cash) / initial_cash

    periods = max(len(values) - 1, 1)
    # US markets have about 252 trading days per year. This compounds the observed
    # return to a yearly rate; short backtests can therefore produce extreme values.
    annualized_return = (final_value / initial_cash) ** (252 / periods) - 1

    # Drawdown measures how far the account fell from its highest value so far.
    running_max = values.cummax()
    drawdowns = values / running_max - 1
    max_drawdown = float(drawdowns.min())

    # pnlcomm is profit after configured commission. This project currently uses
    # Backtrader's default zero commission, so these figures do not include fees.
    winning_trades = []
    losing_trades = []
    for trade in trades:
        pnl = float(trade.get("pnl", 0))
        if pnl > 0:
            winning_trades.append(trade)
        elif pnl < 0:
            losing_trades.append(trade)

    number_of_trades = len(trades)
    # Win rate counts profitable closed trades, not profitable trading days.
    if number_of_trades:
        win_rate = len(winning_trades) / number_of_trades
    else:
        win_rate = 0.0

    if len(returns) > 1 and returns.std():
        # Volatility annualises the spread of daily returns. Sharpe divides average
        # return by that spread and assumes a zero risk-free rate in this prototype.
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
        # Profit factor compares gross gains from winning trades with the absolute
        # gross loss from losing trades. Values above 1 mean gains exceeded losses.
        profit_factor = gross_profit / gross_loss
    else:
        # Zero is the product convention for no losing trades; some platforms show
        # this edge case as infinity instead.
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
