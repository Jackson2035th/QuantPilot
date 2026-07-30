from unittest.mock import patch
from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone
import pytest
from django.urls import reverse
from accounts.models import get_user_profile
from backtests.forms import ConfirmedStrategyForm
from backtests.models import BacktestResult, BacktestRun, Strategy
from backtests.services.llm import LLMProviderError
from backtests.services.market_data import MarketDataError
from backtests.services.schema import ParsedStrategy


def test_landing_page_is_public_and_dashboard_moves_to_workspace(client):
    landing_response = client.get(reverse("landing"))
    dashboard_response = client.get(reverse("dashboard"))

    assert reverse("landing") == "/"
    assert landing_response.status_code == 200
    assert reverse("dashboard") == "/workspace/"
    assert dashboard_response.status_code == 302
    assert "/accounts/login/" in dashboard_response["Location"]


def test_landing_page_presents_the_approved_story_without_chart_axis_numbers(client):
    response = client.get(reverse("landing"))
    content = response.content

    assert b'class="landing-hero"' in content
    assert b"Turn ideas into strategies." in content
    assert b"Test strategies with evidence." in content
    assert b'class="landing-about"' in content
    assert b'class="landing-about-brand"' in content
    assert b'class="landing-about-copy"' in content
    assert b"AI-assisted strategy research for clearer investment decisions." in content
    assert b'class="landing-process"' in content
    assert b'class="landing-mobile-menu"' in content
    assert content.count(b"quantpilot-workflow.png") == 4
    assert b'class="landing-workflow-mobile"' in content
    assert all(label in content for label in (b"01", b"02", b"03", b"04"))
    assert all(
        label in content
        for label in (b"Describe", b"Review", b"Backtest", b"Understand")
    )
    assert b'class="landing-workflow-note"' in content
    assert (
        b"For illustration only. The interface and results shown may differ from actual use."
        in content
    )
    assert b"Your idea" in content
    assert b"Structured parameters" in content
    assert b"Backtest report" in content
    assert b"For educational and research purposes only. Not investment advice." in content
    assert b'aria-label="Animated sample equity curve"' in content
    assert b"hero-axis-label" not in content
    assert b"Strategy parsed" not in content
    assert b"Backtest completed" not in content
    assert b"Risk analysed" not in content
    assert reverse("login").encode() in content
    assert reverse("register").encode() not in content
    assert content.count(b">Start building</a>") == 3
    assert content.count(f'href="{reverse("login")}"'.encode()) == 4
    assert b'class="landing-curve-future"' in content
    assert b'class="landing-curve-glow"' in content
    assert b'class="landing-curve-point"' in content
    assert b"<animateMotion" not in content
    assert b"landing-curve-area" not in content
    assert b"linearGradient" not in content
    curve_path_tag = content.split(b'id="landingCurvePath"', 1)[1].split(b"></path>", 1)[0]
    assert curve_path_tag.count(b" L") >= 270
    assert b'src="/static/js/landing.js"' in content
    assert b"getTotalLength()" not in content
    assert b"getPointAtLength" not in content
    assert b"strokeDash" not in content


def test_login_page_invites_visitors_without_an_account_to_register(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert b"Don't have an account?" in response.content
    assert b"Create an account" in response.content
    assert reverse("register").encode() in response.content


@pytest.mark.django_db
def test_authenticated_landing_page_cta_opens_workspace(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="landing-user", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.get(reverse("landing"))

    assert response.status_code == 200
    assert reverse("dashboard").encode() in response.content
    assert b">Workspace</a>" in response.content
    assert b">Dashboard</a>" not in response.content


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_register_starts_with_username_step(client):
    response = client.post(
        reverse("register"),
        {
            "username": "alice",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("register_email")
    assert not User.objects.filter(username="alice").exists()


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
        "name": "RSI Strategy 1",
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
    assert user.strategy_set.get().name == "RSI Strategy 1"


@pytest.mark.django_db
def test_market_data_failure_saves_a_safe_backtest_error(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="market-error", password="StrongPass123!"
    )
    client.force_login(user)
    payload = {
        "name": "Unavailable data",
        "strategy_type": "ma_crossover",
        "ticker": "AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-03-20",
        "initial_cash": "10000",
        "parameters": '{"short_window": 5, "long_window": 20}',
        "buy_rule": "Buy when short MA crosses above long MA.",
        "sell_rule": "Sell when short MA crosses below long MA.",
    }

    with patch(
        "backtests.views.load_price_data",
        side_effect=MarketDataError("private provider detail"),
    ):
        response = client.post(reverse("run_backtest"), payload)

    run = BacktestRun.objects.get(user=user)
    assert response.status_code == 302
    assert run.status == "failed"
    assert run.completed_at is not None
    assert "private provider detail" not in run.error_message
    assert "Check the ticker and date range" in run.error_message
    assert not BacktestResult.objects.filter(backtest_run=run).exists()


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
    assert b'name="rsi_period"' in response.content
    assert b'name="oversold_threshold"' in response.content
    assert b'name="overbought_threshold"' in response.content
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
    assert b'hx-disabled-elt="find button"' in response.content
    assert b"Parsing strategy..." in response.content
    assert b'class="strategy-prompt-form"' in response.content
    assert b'class="strategy-example-chips"' in response.content
    assert response.content.count(b'data-example-prompt=') == 3


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
        name="RSI Strategy 1",
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
    run = BacktestRun.objects.create(
        user=user,
        strategy=strategy,
        status="completed",
        completed_at=timezone.now(),
    )
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
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert "RSI Strategy 1".encode() in response.content


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
        name="RSI Strategy 1",
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
    assert "RSI Strategy 1".encode() in response.content
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
    assert b'class="history-table"' in response.content
    assert b'class="history-content"' in response.content
    assert b'data-label="Strategy name"' in response.content
    assert b'data-label="Actions"' in response.content


@pytest.mark.django_db
def test_history_searches_the_current_users_strategy_names(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="history-search", password="StrongPass123!"
    )
    matching_strategy = Strategy.objects.create(
        user=user,
        name="RSI Reversal Plan",
        original_prompt="Owner prompt",
        strategy_type="rsi",
        ticker="TSLA",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"rsi_period": 14},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    other_strategy = Strategy.objects.create(
        user=user,
        name="MACD Momentum Plan",
        original_prompt="Owner prompt",
        strategy_type="macd",
        ticker="MSFT",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"fast_period": 12},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    BacktestRun.objects.create(user=user, strategy=matching_strategy, status="completed")
    BacktestRun.objects.create(user=user, strategy=other_strategy, status="completed")

    client.force_login(user)
    response = client.get(reverse("history"), {"q": "rSi"})

    assert response.status_code == 200
    assert b"RSI Reversal Plan" in response.content
    assert b"MACD Momentum Plan" not in response.content
    assert b'value="rSi"' in response.content
    assert b"Clear filters" in response.content

    empty_response = client.get(reverse("history"), {"q": "missing"})
    assert b"No backtests match your filters." in empty_response.content


@pytest.mark.django_db
def test_history_filters_by_ticker_strategy_type_and_date(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="history-filters", password="StrongPass123!"
    )
    matching_strategy = Strategy.objects.create(
        user=user,
        name="AAPL RSI Plan",
        original_prompt="Owner prompt",
        strategy_type="rsi",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"rsi_period": 14},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    other_strategy = Strategy.objects.create(
        user=user,
        name="MSFT MACD Plan",
        original_prompt="Owner prompt",
        strategy_type="macd",
        ticker="MSFT",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"fast_period": 12},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    matching_run = BacktestRun.objects.create(
        user=user,
        strategy=matching_strategy,
        status="completed",
        completed_at="2025-01-15T12:00:00Z",
    )
    BacktestRun.objects.create(
        user=user,
        strategy=other_strategy,
        status="completed",
        completed_at="2025-01-16T12:00:00Z",
    )

    client.force_login(user)
    response = client.get(
        reverse("history"),
        {"ticker": "AAPL", "strategy_type": "rsi", "date": "2025-01-15"},
    )

    assert response.status_code == 200
    assert matching_run.strategy.name.encode() in response.content
    assert b"MSFT MACD Plan" not in response.content
    assert b'<option value="AAPL" selected>' in response.content
    assert b'<option value="rsi" selected>' in response.content
    assert b'value="2025-01-15"' in response.content


@pytest.mark.django_db
def test_history_sorts_total_return_and_keeps_filters(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="history-sort", password="StrongPass123!"
    )
    low_strategy = Strategy.objects.create(
        user=user,
        name="Low return",
        original_prompt="Owner prompt",
        strategy_type="rsi",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"rsi_period": 14},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    high_strategy = Strategy.objects.create(
        user=user,
        name="High return",
        original_prompt="Owner prompt",
        strategy_type="rsi",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"rsi_period": 14},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    low_run = BacktestRun.objects.create(user=user, strategy=low_strategy, status="completed")
    high_run = BacktestRun.objects.create(user=user, strategy=high_strategy, status="completed")
    for run, total_return in ((low_run, 0.05), (high_run, 0.20)):
        BacktestResult.objects.create(
            backtest_run=run,
            total_return=total_return,
            annualized_return=0.1,
            max_drawdown=-0.05,
            number_of_trades=2,
            win_rate=0.5,
            sharpe_ratio=1.0,
            volatility=0.2,
            profit_factor=1.2,
            equity_curve_json=[],
        )

    client.force_login(user)
    response = client.get(
        reverse("history"),
        {"ticker": "AAPL", "sort": "total_return", "order": "desc"},
    )

    assert response.status_code == 200
    assert response.content.index(b"High return") < response.content.index(b"Low return")
    assert b'class="history-sort-arrows"' in response.content
    assert b'history-sort-arrow is-active' in response.content
    assert b'name="ticker"' in response.content
    assert b'value="AAPL" selected' in response.content


@pytest.mark.django_db
def test_history_compares_selected_completed_backtests(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="history-compare", password="StrongPass123!"
    )
    first_strategy = Strategy.objects.create(
        user=user, name="RSI plan", original_prompt="Prompt", strategy_type="rsi",
        ticker="AAPL", start_date="2024-01-01", end_date="2024-03-01",
        initial_cash=10000, parameters_json={"rsi_period": 14}, buy_rule="Buy", sell_rule="Sell",
    )
    second_strategy = Strategy.objects.create(
        user=user, name="MACD plan", original_prompt="Prompt", strategy_type="macd",
        ticker="MSFT", start_date="2024-01-01", end_date="2024-03-01",
        initial_cash=10000, parameters_json={"fast_period": 12}, buy_rule="Buy", sell_rule="Sell",
    )
    first_run = BacktestRun.objects.create(user=user, strategy=first_strategy, status="completed")
    second_run = BacktestRun.objects.create(user=user, strategy=second_strategy, status="completed")
    for run, total_return in ((first_run, 0.1), (second_run, 0.2)):
        BacktestResult.objects.create(
            backtest_run=run, total_return=total_return, annualized_return=0.1,
            max_drawdown=-0.05, number_of_trades=2, win_rate=0.5,
            sharpe_ratio=1.0, volatility=0.2, profit_factor=1.2,
            equity_curve_json=[
                {"date": "2024-01-01", "value": 10000},
                {"date": "2024-01-02", "value": 10000 * (1 + total_return)},
            ],
        )

    client.force_login(user)
    history_response = client.get(reverse("history"))
    response = client.get(
        reverse("compare_backtests"), {"runs": [first_run.id, second_run.id]}
    )

    assert b'form="compare-runs-form"' in history_response.content
    assert b"Compare selected" in history_response.content
    assert response.status_code == 200
    assert b"Equity curve comparison" in response.content
    assert b"RSI plan (AAPL)" in response.content
    assert b"MACD plan (MSFT)" in response.content
    assert b'data-comparison-chart' in response.content


@pytest.mark.django_db
def test_history_comparison_requires_two_completed_backtests(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="history-compare-error", password="StrongPass123!"
    )

    client.force_login(user)
    response = client.get(reverse("compare_backtests"), {"runs": [1]})

    assert response.status_code == 400
    assert b"Choose between 2 and 4 completed backtests" in response.content


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


def test_guide_is_public(client):
    response = client.get(reverse("guide"))

    assert response.status_code == 200
    assert b"How QuantPilot works" in response.content
    assert b"public-guide-main" in response.content
    assert reverse("landing").encode() in response.content
    assert b"Log in" in response.content


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
    assert b"account-menu" in response.content
    assert b"logout-control" in response.content


@pytest.mark.django_db
def test_logout_returns_to_the_public_landing_page(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="logout-landing", password="StrongPass123!"
    )
    client.force_login(user)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response["Location"] == reverse("landing")


@pytest.mark.django_db
def test_profile_page_shows_account_summary_and_updates_display_name(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        username="profile-owner", password="StrongPass123!"
    )
    client.force_login(user)

    profile_page = client.get(reverse("profile"))
    update_response = client.post(
        reverse("profile"), {"display_name": "Quant Trader"}
    )

    profile = get_user_profile(user)
    profile.refresh_from_db()
    assert profile_page.status_code == 200
    assert b"Account profile" in profile_page.content
    assert b"Completed backtests" in profile_page.content
    assert update_response.status_code == 302
    assert profile.display_name == "Quant Trader"


@pytest.mark.django_db
def test_restart_onboarding_marks_the_guide_as_incomplete(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="restart-guide", password="StrongPass123!"
    )
    profile = get_user_profile(user)
    profile.has_completed_onboarding = True
    profile.save(update_fields=["has_completed_onboarding"])
    client.force_login(user)

    response = client.post(reverse("restart_onboarding"))

    profile.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")
    assert profile.has_completed_onboarding is False


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
    glossary_terms = [term for term, _ in response.context["guide_glossary"]]
    assert len(glossary_terms) == 10
    assert "Volatility" in glossary_terms
    assert "Annualized return" in glossary_terms
    assert "Backtest" not in glossary_terms
    assert glossary_terms[-2:] == ["Annualized return", "Volatility"]


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
    assert b'class="sidebar-toggle"' in response.content
    assert b'aria-controls="primary-navigation"' in response.content
    assert b'class="sidebar-backdrop"' in response.content
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
    assert b"Volatility" in response.content
    assert b"Equity curve" in response.content
    assert b'class="result-chart-container"' in response.content
    assert b"equityChart" in response.content
    assert b'src="/static/js/equity-chart.js"' in response.content
    assert b'data-equity-source="equity-data"' in response.content


def _create_dashboard_run(user, name, status, completed_at=None):
    strategy = Strategy.objects.create(
        user=user,
        name=name,
        original_prompt="Dashboard prompt",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    run = BacktestRun.objects.create(
        user=user,
        strategy=strategy,
        status=status,
        completed_at=completed_at,
    )
    if status == "completed":
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
            equity_curve_json=[
                {"date": "2024-01-01", "value": 10000},
                {"date": "2024-03-01", "value": 11000},
            ],
            metrics_json={"total_return": 0.1},
        )
    return run


@pytest.mark.django_db
def test_dashboard_features_only_the_current_users_latest_completed_run(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        username="featured-dashboard", password="StrongPass123!"
    )
    other_user = django_user_model.objects.create_user(
        username="other-dashboard", password="StrongPass123!"
    )
    earlier = _create_dashboard_run(
        user,
        "Earlier completed strategy",
        "completed",
        timezone.now() - timezone.timedelta(days=2),
    )
    featured = _create_dashboard_run(
        user,
        "Latest completed strategy",
        "completed",
        timezone.now() - timezone.timedelta(days=1),
    )
    _create_dashboard_run(user, "Pending strategy", "pending")
    _create_dashboard_run(user, "Failed strategy", "failed", timezone.now())
    _create_dashboard_run(
        other_user,
        "Other user strategy",
        "completed",
        timezone.now() + timezone.timedelta(days=1),
    )

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["featured_run"] == featured
    assert response.context["featured_metric_cards"]
    assert len(response.context["featured_metric_cards"]) == 5
    assert response.context["takeaways"]
    assert b"Latest completed backtest" in response.content
    assert b"Latest completed strategy" in response.content
    assert b"Earlier completed strategy" not in response.content
    assert b"Pending strategy" not in response.content
    assert b"Failed strategy" not in response.content
    assert b"Other user strategy" not in response.content
    assert reverse("result_detail", args=[featured.id]).encode() in response.content
    assert reverse("edit_backtest", args=[featured.id]).encode() in response.content
    assert b"dashboardEquityChart" in response.content
    assert b"dashboard-chart-fallback" in response.content
    assert b"Equity curve preview is unavailable for this backtest." in response.content
    assert b"Backtest highlights" in response.content
    assert b'src="/static/js/equity-chart.js"' in response.content
    assert b'data-equity-source="dashboard-equity-data"' in response.content
    assert b"Explain this result with AI" in response.content
    assert b"Generating explanation..." in response.content
    assert b'hx-disabled-elt="find button"' in response.content
    assert reverse("dashboard_ai_explanation").encode() in response.content
    assert b'<form class="ai-explanation-form" method="post"' in response.content
    assert b"Recent backtests" not in response.content
    assert b'data-lucide="layout-dashboard"' in response.content
    assert b'data-lucide="circle-plus"' in response.content


@pytest.mark.django_db
def test_dashboard_empty_state_has_first_backtest_actions_without_chart_or_metrics(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        username="empty-dashboard", password="StrongPass123!"
    )
    _create_dashboard_run(user, "Pending strategy", "pending")
    _create_dashboard_run(user, "Failed strategy", "failed", timezone.now())

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["featured_run"] is None
    assert response.context["featured_metric_cards"] == []
    assert response.context["takeaways"] == []
    assert b"Start your first backtest" in response.content
    assert b"Use an example" in response.content
    assert b"Open Guide" in response.content
    assert b"dashboardEquityChart" not in response.content
    assert b"dashboard-metric-grid" not in response.content


@pytest.mark.django_db
def test_dashboard_ai_explanation_requires_login_and_post(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="ai-method", password="StrongPass123!"
    )

    anonymous_response = client.post(reverse("dashboard_ai_explanation"))
    client.force_login(user)
    get_response = client.get(reverse("dashboard_ai_explanation"))

    assert anonymous_response.status_code == 302
    assert get_response.status_code == 405


@pytest.mark.django_db
def test_dashboard_ai_explanation_uses_only_current_users_latest_completed_run(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        username="ai-owner", password="StrongPass123!"
    )
    other_user = django_user_model.objects.create_user(
        username="ai-other", password="StrongPass123!"
    )
    own_run = _create_dashboard_run(
        user, "Owner strategy", "completed", timezone.now() - timezone.timedelta(days=1)
    )
    _create_dashboard_run(
        other_user, "Other strategy", "completed", timezone.now()
    )
    client.force_login(user)

    with patch("backtests.views.DeepSeekProvider.explain_backtest", return_value="A careful summary.") as explain:
        response = client.post(reverse("dashboard_ai_explanation"))

    assert response.status_code == 200
    assert b"AI explanation" in response.content
    assert b"A careful summary." in response.content
    assert explain.call_args.args[0] == own_run.strategy
    assert explain.call_args.args[1] == own_run.result


@pytest.mark.django_db
def test_dashboard_ai_explanation_shows_inline_error_and_empty_state(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="ai-errors", password="StrongPass123!"
    )
    client.force_login(user)

    empty_response = client.post(reverse("dashboard_ai_explanation"))
    assert empty_response.status_code == 200
    assert b"There is no completed backtest available to explain yet." in empty_response.content

    _create_dashboard_run(user, "Failed AI", "completed", timezone.now())
    with patch(
        "backtests.views.DeepSeekProvider.explain_backtest",
        side_effect=LLMProviderError("Provider unavailable"),
    ):
        error_response = client.post(reverse("dashboard_ai_explanation"))

    assert error_response.status_code == 200
    assert b"Unable to generate an AI explanation right now." in error_response.content
