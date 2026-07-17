from unittest.mock import patch
from datetime import date

from django.contrib.auth.models import User
import pytest
from django.urls import reverse
from backtests.forms import ConfirmedStrategyForm
from backtests.models import BacktestResult, BacktestRun, Strategy
from backtests.services.schema import ParsedStrategy


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_user_can_register_and_is_redirected_to_dashboard(client):
    response = client.post(
        reverse("register"),
        {
            "username": "alice",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")
    assert User.objects.filter(username="alice").exists()


@pytest.mark.django_db
def test_strategy_belongs_to_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="bob", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="AAPL MA",
        original_prompt="Backtest AAPL moving average crossover.",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_cash=10000,
        parameters_json={"short_window": 20, "long_window": 50},
        buy_rule="Buy rule",
        sell_rule="Sell rule",
    )

    assert strategy.user == user
    assert str(strategy) == "AAPL MA"


@pytest.mark.django_db
def test_authenticated_user_can_run_confirmed_backtest(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="carol", password="StrongPass123!"
    )
    client.force_login(user)
    payload = {
        "name": "RSI1号策略",
        "strategy_type": "ma_crossover",
        "ticker": "AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-03-20",
        "initial_cash": "10000",
        "parameters": '{"short_window": 5, "long_window": 20}',
        "buy_rule": "Buy when short MA crosses above long MA.",
        "sell_rule": "Sell when short MA crosses below long MA.",
    }

    with patch("backtests.views.load_price_data") as load_price_data:
        with patch("backtests.views.run_backtest") as run_backtest:
            load_price_data.return_value = object()
            run_backtest.return_value.equity_curve = [
                {"date": "2024-01-01", "value": 10000.0}
            ]
            run_backtest.return_value.metrics = {
                "total_return": 0.1,
                "annualized_return": 0.2,
                "max_drawdown": -0.05,
                "number_of_trades": 3,
                "win_rate": 0.67,
                "sharpe_ratio": 1.1,
                "volatility": 0.2,
                "profit_factor": 2.0,
            }
            response = client.post(reverse("run_backtest"), payload)

    assert response.status_code == 302
    assert user.strategy_set.count() == 1
    assert user.strategy_set.get().name == "RSI1号策略"


@pytest.mark.django_db
def test_parse_strategy_includes_default_strategy_name(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="parsed-name", password="StrongPass123!"
    )
    client.force_login(user)
    parsed = ParsedStrategy(
        strategy_type="rsi",
        ticker="AAPL",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 1),
        initial_cash=10000,
        parameters={
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
        },
        buy_rule="Buy when RSI is below 30.",
        sell_rule="Sell when RSI is above 70.",
    )

    with patch("backtests.views.DeepSeekProvider") as provider:
        provider.return_value.parse_strategy.return_value = parsed
        response = client.post(
            reverse("parse_strategy"),
            {"prompt": "Backtest Apple stock with an RSI strategy."},
        )

    assert response.status_code == 200
    assert b'name="name"' in response.content
    assert b'value="AAPL rsi"' in response.content
    assert b"Advanced strategy details" in response.content


@pytest.mark.django_db
def test_strategy_input_form_disables_browser_native_validation(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="prompt-page", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("strategy_input"))

    assert response.status_code == 200
    assert b"novalidate" in response.content


@pytest.mark.django_db
def test_parse_strategy_rejects_empty_prompt_in_english(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="empty-prompt", password="StrongPass123!"
    )
    client.force_login(user)

    with patch("backtests.views.DeepSeekProvider") as provider:
        response = client.post(reverse("parse_strategy"), {"prompt": ""})

    assert response.status_code == 200
    assert b"Enter a strategy description." in response.content
    provider.assert_not_called()


@pytest.mark.django_db
def test_parse_strategy_rejects_numeric_prompt(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="numeric-prompt", password="StrongPass123!"
    )
    client.force_login(user)

    with patch("backtests.views.DeepSeekProvider") as provider:
        response = client.post(reverse("parse_strategy"), {"prompt": "3"})

    assert response.status_code == 200
    assert b"Enter a valid strategy description." in response.content
    provider.assert_not_called()


@pytest.mark.django_db
def test_parse_strategy_rejects_random_letters(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="random-prompt", password="StrongPass123!"
    )
    client.force_login(user)

    with patch("backtests.views.DeepSeekProvider") as provider:
        response = client.post(reverse("parse_strategy"), {"prompt": "abcdefg xyz"})

    assert response.status_code == 200
    assert b"Enter a valid strategy description." in response.content
    provider.assert_not_called()


def test_confirmed_strategy_form_rejects_future_dates():
    form = ConfirmedStrategyForm(
        data={
            "strategy_type": "ma_crossover",
            "name": "Future date test",
            "ticker": "AAPL",
            "start_date": "2999-01-01",
            "end_date": "2999-12-31",
            "initial_cash": "10000",
            "parameters": '{"short_window": 5, "long_window": 20}',
            "buy_rule": "Buy when short MA crosses above long MA.",
            "sell_rule": "Sell when short MA crosses below long MA.",
        }
    )

    assert not form.is_valid()
    assert "start_date" in form.errors
    assert "end_date" in form.errors


@pytest.mark.django_db
def test_dashboard_shows_strategy_name(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="dashboard-name", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="RSI1号策略",
        original_prompt="Named prompt",
        strategy_type="rsi",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
        },
        buy_rule="Buy",
        sell_rule="Sell",
    )
    BacktestRun.objects.create(user=user, strategy=strategy, status="completed")

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert "RSI1号策略".encode() in response.content


@pytest.mark.django_db
def test_user_cannot_view_another_users_result(client, django_user_model):
    owner = django_user_model.objects.create_user(
        username="owner", password="StrongPass123!"
    )
    other = django_user_model.objects.create_user(
        username="other", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=owner,
        name="Private strategy",
        original_prompt="Private prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=owner, strategy=strategy, status="completed")
    BacktestResult.objects.create(
        backtest_run=run,
        total_return=0.1,
        annualized_return=0.2,
        max_drawdown=-0.05,
        number_of_trades=2,
        win_rate=0.5,
        sharpe_ratio=1.0,
        volatility=0.2,
        profit_factor=2.0,
        equity_curve_json=[{"date": "2024-01-01", "value": 10000}],
        metrics_json={"total_return": 0.1},
    )

    client.force_login(other)
    response = client.get(reverse("result_detail", args=[run.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_result_detail_shows_strategy_name_and_metadata(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="result-name", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="RSI1号策略",
        original_prompt="Named prompt",
        strategy_type="rsi",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
        },
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=user, strategy=strategy, status="completed")
    BacktestResult.objects.create(
        backtest_run=run,
        total_return=0.1,
        annualized_return=0.2,
        max_drawdown=-0.05,
        number_of_trades=2,
        win_rate=0.5,
        sharpe_ratio=1.0,
        volatility=0.2,
        profit_factor=2.0,
        equity_curve_json=[{"date": "2024-01-01", "value": 10000}],
        metrics_json={"total_return": 0.1},
    )

    client.force_login(user)
    response = client.get(reverse("result_detail", args=[run.id]))

    assert response.status_code == 200
    assert "RSI1号策略".encode() in response.content
    assert b"AAPL" in response.content
    assert b"rsi" in response.content


@pytest.mark.django_db
def test_history_shows_only_current_users_runs(client, django_user_model):
    owner = django_user_model.objects.create_user(
        username="history-owner", password="StrongPass123!"
    )
    other = django_user_model.objects.create_user(
        username="history-other", password="StrongPass123!"
    )
    owner_strategy = Strategy.objects.create(
        user=owner,
        name="Owner strategy",
        original_prompt="Owner prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    other_strategy = Strategy.objects.create(
        user=other,
        name="Other strategy",
        original_prompt="Other prompt",
        strategy_type="ma_crossover",
        ticker="MSFT",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    BacktestRun.objects.create(
        user=owner, strategy=owner_strategy, status="completed"
    )
    BacktestRun.objects.create(
        user=other, strategy=other_strategy, status="completed"
    )

    client.force_login(owner)
    response = client.get(reverse("history"))

    assert response.status_code == 200
    assert b"Owner strategy" in response.content
    assert b"AAPL" in response.content
    assert b"Other strategy" not in response.content
    assert b"MSFT" not in response.content


@pytest.mark.django_db
def test_history_shows_edit_and_delete_actions(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="history-actions", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="Editable strategy",
        original_prompt="Owner prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=user, strategy=strategy, status="completed")

    client.force_login(user)
    response = client.get(reverse("history"))

    assert response.status_code == 200
    assert reverse("edit_backtest", args=[run.id]).encode() in response.content
    assert reverse("delete_backtest", args=[run.id]).encode() in response.content


@pytest.mark.django_db
def test_edit_backtest_page_shows_existing_parameters(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="edit-page", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="Editable strategy",
        original_prompt="Owner prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=user, strategy=strategy, status="completed")

    client.force_login(user)
    response = client.get(reverse("edit_backtest", args=[run.id]))

    assert response.status_code == 200
    assert b"Editable strategy" in response.content
    assert b"AAPL" in response.content
    assert b"&quot;short_window&quot;: 5" in response.content
    assert b"Advanced strategy details" in response.content


@pytest.mark.django_db
def test_user_cannot_edit_another_users_backtest(client, django_user_model):
    owner = django_user_model.objects.create_user(
        username="edit-owner", password="StrongPass123!"
    )
    other = django_user_model.objects.create_user(
        username="edit-other", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=owner,
        name="Private editable strategy",
        original_prompt="Private prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=owner, strategy=strategy, status="completed")

    client.force_login(other)
    response = client.get(reverse("edit_backtest", args=[run.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_edit_backtest_reruns_and_updates_existing_record(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="edit-rerun", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="Original name",
        original_prompt="Owner prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=user, strategy=strategy, status="completed")
    BacktestResult.objects.create(
        backtest_run=run,
        total_return=0.1,
        annualized_return=0.2,
        max_drawdown=-0.05,
        number_of_trades=2,
        win_rate=0.5,
        sharpe_ratio=1.0,
        volatility=0.2,
        profit_factor=2.0,
        equity_curve_json=[{"date": "2024-01-01", "value": 10000}],
        metrics_json={"total_return": 0.1},
    )
    payload = {
        "name": "Updated name",
        "strategy_type": "ma_crossover",
        "ticker": "MSFT",
        "start_date": "2024-01-01",
        "end_date": "2024-03-20",
        "initial_cash": "15000",
        "parameters": '{"short_window": 6, "long_window": 25}',
        "buy_rule": "Buy when short MA crosses above long MA.",
        "sell_rule": "Sell when short MA crosses below long MA.",
    }

    client.force_login(user)
    with patch("backtests.views.load_price_data") as load_price_data:
        with patch("backtests.views.run_backtest") as run_backtest:
            load_price_data.return_value = object()
            run_backtest.return_value.equity_curve = [
                {"date": "2024-01-01", "value": 15000.0}
            ]
            run_backtest.return_value.metrics = {
                "total_return": 0.2,
                "annualized_return": 0.3,
                "max_drawdown": -0.04,
                "number_of_trades": 4,
                "win_rate": 0.75,
                "sharpe_ratio": 1.3,
                "volatility": 0.25,
                "profit_factor": 2.5,
            }
            response = client.post(reverse("edit_backtest", args=[run.id]), payload)

    assert response.status_code == 302
    assert response["Location"] == reverse("result_detail", args=[run.id])
    strategy.refresh_from_db()
    run.refresh_from_db()
    run.result.refresh_from_db()
    assert Strategy.objects.count() == 1
    assert BacktestRun.objects.count() == 1
    assert strategy.name == "Updated name"
    assert strategy.ticker == "MSFT"
    assert strategy.parameters_json == {"short_window": 6, "long_window": 25}
    assert run.status == "completed"
    assert run.result.total_return == 0.2


@pytest.mark.django_db
def test_delete_backtest_removes_users_run_and_strategy(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="delete-owner", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="Delete me",
        original_prompt="Owner prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=user, strategy=strategy, status="completed")

    client.force_login(user)
    response = client.post(reverse("delete_backtest", args=[run.id]))

    assert response.status_code == 302
    assert response["Location"] == reverse("history")
    assert BacktestRun.objects.count() == 0
    assert Strategy.objects.count() == 0


@pytest.mark.django_db
def test_user_cannot_delete_another_users_backtest(client, django_user_model):
    owner = django_user_model.objects.create_user(
        username="delete-real-owner", password="StrongPass123!"
    )
    other = django_user_model.objects.create_user(
        username="delete-other", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=owner,
        name="Private delete",
        original_prompt="Owner prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=owner, strategy=strategy, status="completed")

    client.force_login(other)
    response = client.post(reverse("delete_backtest", args=[run.id]))

    assert response.status_code == 404
    assert BacktestRun.objects.count() == 1
    assert Strategy.objects.count() == 1


@pytest.mark.django_db
def test_guide_requires_login(client):
    response = client.get(reverse("guide"))

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_authenticated_shell_renders_a_post_logout_form(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="logout-control", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert b'<form class="logout-form" method="post"' in response.content
    assert reverse("logout").encode() in response.content


@pytest.mark.django_db
def test_guide_lists_actionable_english_examples(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="guide-reader", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("guide"))

    assert response.status_code == 200
    assert b"How QuantPilot works" in response.content
    assert b"Moving Average Crossover" in response.content
    assert b"Use this example" in response.content


@pytest.mark.django_db
def test_strategy_input_prefills_prompt_from_guide_example(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="prefill-reader", password="StrongPass123!"
    )
    client.force_login(user)
    prompt = "Backtest AAPL with an RSI strategy from 2020-01-01 to 2024-12-31."

    response = client.get(reverse("strategy_input"), {"prompt": prompt})

    assert response.status_code == 200
    assert prompt.encode() in response.content


@pytest.mark.django_db
def test_new_user_sees_onboarding_until_they_skip(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="first-visit", password="StrongPass123!"
    )
    client.force_login(user)

    first_dashboard = client.get(reverse("dashboard"))
    skipped = client.post(reverse("complete_onboarding"))
    later_dashboard = client.get(reverse("dashboard"))

    assert b"Welcome to QuantPilot" in first_dashboard.content
    assert skipped.status_code == 302
    assert later_dashboard.status_code == 200
    assert b"Welcome to QuantPilot" not in later_dashboard.content


@pytest.mark.django_db
def test_complete_onboarding_rejects_get_requests(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="onboarding-method", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("complete_onboarding"))

    assert response.status_code == 405


@pytest.mark.django_db
def test_dashboard_uses_application_navigation_and_new_user_onboarding(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        username="dashboard-shell", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert b"app-sidebar" in response.content
    assert reverse("strategy_input").encode() in response.content
    assert reverse("history").encode() in response.content
    assert reverse("guide").encode() in response.content
    assert b"Welcome to QuantPilot" in response.content
    assert b"Create a strategy" in response.content


@pytest.mark.django_db
def test_strategy_builder_shows_input_checklist_and_examples(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="builder-guide", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("strategy_input"))

    assert b"What to include" in response.content
    assert b"Moving Average Crossover" in response.content
    assert b"RSI Reversal" in response.content
    assert b"MACD Crossover" in response.content


@pytest.mark.django_db
def test_completed_result_uses_named_metric_cards_and_equity_chart(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        username="metric-cards", password="StrongPass123!"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="AAPL crossover",
        original_prompt="Prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(user=user, strategy=strategy, status="completed")
    BacktestResult.objects.create(
        backtest_run=run,
        total_return=0.1,
        annualized_return=0.2,
        max_drawdown=-0.05,
        number_of_trades=2,
        win_rate=0.5,
        sharpe_ratio=1.0,
        volatility=0.2,
        profit_factor=2.0,
        equity_curve_json=[{"date": "2024-01-01", "value": 10000}],
        metrics_json={"total_return": 0.1},
    )
    client.force_login(user)

    response = client.get(reverse("result_detail", args=[run.id]))

    assert b"Total Return" in response.content
    assert b"10.00%" in response.content
    assert b"Maximum Drawdown" in response.content
    assert b"Equity curve" in response.content
    assert b"equityChart" in response.content
