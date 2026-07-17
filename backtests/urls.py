from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("strategies/new/", views.strategy_input, name="strategy_input"),
    path("strategies/parse/", views.parse_strategy, name="parse_strategy"),
    path("guide/", views.guide, name="guide"),
    path("onboarding/complete/", views.complete_onboarding, name="complete_onboarding"),
    path("backtests/run/", views.run_confirmed_backtest, name="run_backtest"),
    path("backtests/history/", views.history, name="history"),
    path("backtests/<int:run_id>/edit/", views.edit_backtest, name="edit_backtest"),
    path(
        "backtests/<int:run_id>/delete/",
        views.delete_backtest,
        name="delete_backtest",
    ),
    path("backtests/<int:run_id>/", views.result_detail, name="result_detail"),
]
