def _percent(value):
    return f"{value * 100:.2f}%"


def build_metric_cards(result):
    return [
        {
            "label": "Total Return",
            "value": _percent(result.total_return),
            "tone": "positive" if result.total_return >= 0 else "negative",
        },
        {
            "label": "Annualized Return",
            "value": _percent(result.annualized_return),
            "tone": "positive" if result.annualized_return >= 0 else "negative",
        },
        {"label": "Sharpe Ratio", "value": f"{result.sharpe_ratio:.2f}", "tone": "neutral"},
        {
            "label": "Maximum Drawdown",
            "value": _percent(result.max_drawdown),
            "tone": "negative",
        },
        {"label": "Win Rate", "value": _percent(result.win_rate), "tone": "neutral"},
        {"label": "Profit Factor", "value": f"{result.profit_factor:.2f}", "tone": "neutral"},
        {"label": "Number of Trades", "value": str(result.number_of_trades), "tone": "neutral"},
        {"label": "Volatility", "value": _percent(result.volatility), "tone": "neutral"},
    ]


def build_dashboard_metric_cards(result):
    featured_labels = {
        "Total Return",
        "Annualized Return",
        "Sharpe Ratio",
        "Maximum Drawdown",
        "Win Rate",
    }
    return [card for card in build_metric_cards(result) if card["label"] in featured_labels]


def build_takeaways(result):
    if result.total_return > 0:
        performance = "positive"
    elif result.total_return < 0:
        performance = "negative"
    else:
        performance = "flat"

    drawdown = abs(result.max_drawdown)
    if drawdown < 0.10:
        drawdown_severity = "limited"
    elif drawdown < 0.25:
        drawdown_severity = "meaningful"
    else:
        drawdown_severity = "severe"

    return [
        f"This backtest had a {performance} total return of {_percent(result.total_return)}.",
        f"Its largest peak-to-trough decline was {drawdown * 100:.2f}%, which was {drawdown_severity}.",
        f"The Win Rate was {_percent(result.win_rate)}, and the Sharpe Ratio was {result.sharpe_ratio:.2f}.",
        "Historical results do not guarantee future performance.",
    ]


def build_history_rows(runs):
    rows = []
    for run in runs:
        total_return = "-"
        if run.status == "completed" and hasattr(run, "result"):
            total_return = _percent(run.result.total_return)
        rows.append({"run": run, "total_return": total_return})
    return rows
