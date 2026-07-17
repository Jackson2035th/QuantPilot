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
    ]


def build_history_rows(runs):
    rows = []
    for run in runs:
        total_return = "-"
        if run.status == "completed" and hasattr(run, "result"):
            total_return = _percent(run.result.total_return)
        rows.append({"run": run, "total_return": total_return})
    return rows
