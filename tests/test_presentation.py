from types import SimpleNamespace

from backtests.presentation import build_dashboard_metric_cards, build_metric_cards, build_takeaways


def make_result(**overrides):
    values = {
        "total_return": 0.2734,
        "annualized_return": 0.1455,
        "sharpe_ratio": 1.28,
        "max_drawdown": -0.1642,
        "win_rate": 0.5667,
        "profit_factor": 1.62,
        "number_of_trades": 82,
        "volatility": 0.2134,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_dashboard_metric_cards_keeps_the_featured_metrics_in_existing_order():
    cards = build_dashboard_metric_cards(make_result())

    assert [card["label"] for card in cards] == [
        "Total Return",
        "Annualized Return",
        "Sharpe Ratio",
        "Maximum Drawdown",
        "Win Rate",
    ]
    assert cards[0]["value"] == "27.34%"
    assert cards[3]["value"] == "-16.42%"


def test_build_metric_cards_includes_volatility_as_the_eighth_card():
    cards = build_metric_cards(make_result())

    assert len(cards) == 8
    assert cards[-1] == {"label": "Volatility", "value": "21.34%", "tone": "neutral"}


def test_build_takeaways_describes_a_positive_result_in_plain_english():
    takeaways = build_takeaways(make_result())

    assert isinstance(takeaways, list)
    assert takeaways == [
        "This backtest had a positive total return of 27.34%.",
        "Its largest peak-to-trough decline was 16.42%, which was meaningful.",
        "The Win Rate was 56.67%, and the Sharpe Ratio was 1.28.",
        "Historical results do not guarantee future performance.",
    ]


def test_build_takeaways_describes_negative_and_flat_results_sensibly():
    negative = build_takeaways(make_result(total_return=-0.083, max_drawdown=-0.24))
    flat = build_takeaways(make_result(total_return=0.0, max_drawdown=0.0))

    assert len(negative) == 4
    assert negative[0] == "This backtest had a negative total return of -8.30%."
    assert negative[1] == "Its largest peak-to-trough decline was 24.00%, which was meaningful."
    assert flat[0] == "This backtest had a flat total return of 0.00%."
    assert flat[1] == "Its largest peak-to-trough decline was 0.00%, which was limited."
    assert all(takeaways[-1] == "Historical results do not guarantee future performance." for takeaways in [negative, flat])


def test_build_takeaways_classifies_drawdown_threshold_boundaries():
    limited = build_takeaways(make_result(max_drawdown=-0.0999))
    meaningful_at_boundary = build_takeaways(make_result(max_drawdown=-0.10))
    meaningful = build_takeaways(make_result(max_drawdown=-0.2499))
    severe_at_boundary = build_takeaways(make_result(max_drawdown=-0.25))

    assert limited[1] == "Its largest peak-to-trough decline was 9.99%, which was limited."
    assert meaningful_at_boundary[1] == "Its largest peak-to-trough decline was 10.00%, which was meaningful."
    assert meaningful[1] == "Its largest peak-to-trough decline was 24.99%, which was meaningful."
    assert severe_at_boundary[1] == "Its largest peak-to-trough decline was 25.00%, which was severe."
