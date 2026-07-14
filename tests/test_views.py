from unittest.mock import patch

from django.contrib.auth.models import User
import pytest
from django.urls import reverse
from backtests.models import Strategy


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
