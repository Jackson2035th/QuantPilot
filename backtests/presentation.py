def _percent(value):
    return f"{value * 100:.2f}%"


def build_metric_cards(result):
    # Tone controls colour only; the saved metric values remain unchanged.
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
    # The dashboard uses a smaller summary than the full result page.
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

    # Drawdown is stored as a negative return, but its size is clearer as positive text.
    drawdown = abs(result.max_drawdown)
    # These broad bands create plain-language context, not an investment rating.
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
        # Failed or unfinished runs have no result and cannot be compared.
        can_compare = run.status == "completed" and hasattr(run, "result")
        if can_compare:
            total_return = _percent(run.result.total_return)
        rows.append(
            {"run": run, "total_return": total_return, "can_compare": can_compare}
        )
    return rows


def build_comparison_rows(runs):
    # Format every selected run consistently before the template builds the table.
    rows = []
    for run in runs:
        result = run.result
        rows.append(
            {
                "run": run,
                "total_return": _percent(result.total_return),
                "annualized_return": _percent(result.annualized_return),
                "max_drawdown": _percent(result.max_drawdown),
                "win_rate": _percent(result.win_rate),
                "sharpe_ratio": f"{result.sharpe_ratio:.2f}",
            }
        )
    return rows
