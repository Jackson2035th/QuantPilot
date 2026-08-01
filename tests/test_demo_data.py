from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from backtests.management.commands.seed_demo_data import DEMO_PREFIX
from backtests.models import BacktestRun, Strategy
from backtests.services.market_data import MarketDataError


def _yfinance_like_price_data():
    dates = pd.bdate_range("2022-01-03", "2024-12-31")
    close = [100 + index * 0.08 + (index % 17) * 0.15 for index in range(len(dates))]
    return pd.DataFrame(
        {
            "open": close,
            "high": [value * 1.01 for value in close],
            "low": [value * 0.99 for value in close],
            "close": close,
            "volume": [1_000_000] * len(dates),
        },
        index=dates,
    )


@pytest.mark.django_db
def test_seed_demo_data_is_complete_repeatable_and_preserves_personal_data(
    django_user_model,
):
    with patch(
        "backtests.management.commands.seed_demo_data.load_price_data",
        return_value=_yfinance_like_price_data(),
    ) as load_price_data:
        call_command(
            "seed_demo_data",
            username="quantpilot_demo",
            password="LocalDemoPass123!",
        )

    user = django_user_model.objects.get(username="quantpilot_demo")
    demo_strategies = Strategy.objects.filter(
        user=user,
        original_prompt__startswith=DEMO_PREFIX,
    )
    demo_runs = BacktestRun.objects.filter(strategy__in=demo_strategies)

    assert user.check_password("LocalDemoPass123!")
    assert user.userprofile.has_completed_onboarding is True
    assert demo_strategies.count() == 16
    assert demo_runs.filter(status="completed").count() == 15
    assert demo_runs.filter(status="failed").count() == 1
    assert demo_runs.filter(status="completed", result__isnull=True).count() == 0
    assert set(demo_strategies.values_list("ticker", flat=True)) == {
        "AAPL",
        "AMZN",
        "MSFT",
        "NVDA",
        "TSLA",
    }
    for strategy_type in ("ma_crossover", "rsi", "macd"):
        assert demo_runs.filter(
            status="completed",
            strategy__strategy_type=strategy_type,
        ).count() == 5
    assert demo_strategies.filter(end_date__gt=date.today()).count() == 0
    assert all(
        strategy.ticker in strategy.name for strategy in demo_strategies
    )
    assert set(demo_runs.values_list("data_source", flat=True)) == {"yfinance"}
    assert set(demo_runs.values_list("engine", flat=True)) == {"backtrader"}
    assert all(run.data_source_label == "yfinance" for run in demo_runs)
    assert load_price_data.call_count == 5

    first_result = demo_runs.filter(status="completed").first().result
    assert len(first_result.equity_curve_json) > 700
    assert first_result.metrics_json["total_return"] == first_result.total_return

    personal_strategy = Strategy.objects.create(
        user=user,
        name="Personal AAPL MA",
        original_prompt="A personal record that the demo reset must preserve.",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2023-01-01",
        end_date="2024-12-31",
        initial_cash=10_000,
        parameters_json={"short_window": 20, "long_window": 50},
        buy_rule="Buy on an upward moving-average crossover.",
        sell_rule="Sell on a downward moving-average crossover.",
    )

    with pytest.raises(CommandError, match="already exist"):
        call_command("seed_demo_data", username="quantpilot_demo")

    original_demo_strategy_ids = set(demo_strategies.values_list("id", flat=True))
    with patch(
        "backtests.management.commands.seed_demo_data.load_price_data",
        side_effect=MarketDataError("yfinance is temporarily unavailable"),
    ):
        with pytest.raises(CommandError, match="no demo records were replaced"):
            call_command(
                "seed_demo_data",
                username="quantpilot_demo",
                password="UpdatedLocalDemoPass123!",
                reset=True,
            )
    assert set(
        Strategy.objects.filter(
            user=user,
            original_prompt__startswith=DEMO_PREFIX,
        ).values_list("id", flat=True)
    ) == original_demo_strategy_ids

    with patch(
        "backtests.management.commands.seed_demo_data.load_price_data",
        return_value=_yfinance_like_price_data(),
    ):
        call_command(
            "seed_demo_data",
            username="quantpilot_demo",
            password="UpdatedLocalDemoPass123!",
            reset=True,
        )

    user.refresh_from_db()
    assert user.check_password("UpdatedLocalDemoPass123!")
    assert Strategy.objects.filter(pk=personal_strategy.pk).exists()
    assert Strategy.objects.filter(
        user=user,
        original_prompt__startswith=DEMO_PREFIX,
    ).count() == 16
