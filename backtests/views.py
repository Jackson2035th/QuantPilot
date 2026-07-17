import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ConfirmedStrategyForm, StrategyPromptForm
from .models import BacktestResult, BacktestRun, Strategy
from .services.engine import run_backtest
from .services.llm import DeepSeekProvider, LLMProviderError
from .services.market_data import load_price_data
from .services.schema import (
    StrategyValidationError,
    parse_strategy_payload,
    strategy_to_dict,
)


@login_required
def dashboard(request):
    recent_runs = BacktestRun.objects.filter(user=request.user).select_related(
        "strategy"
    )[:5]
    return render(request, "backtests/dashboard.html", {"recent_runs": recent_runs})


@login_required
def strategy_input(request):
    return render(request, "backtests/strategy_input.html", {"form": StrategyPromptForm()})


@login_required
def parse_strategy(request):
    form = StrategyPromptForm(request.POST)
    if not form.is_valid():
        message = form.errors["prompt"][0]
        return render(
            request,
            "backtests/partials/parse_error.html",
            {"message": message},
        )

    provider = DeepSeekProvider(
        settings.DEEPSEEK_API_KEY,
        settings.DEEPSEEK_BASE_URL,
        settings.DEEPSEEK_MODEL,
    )
    try:
        parsed = provider.parse_strategy(form.cleaned_data["prompt"])
    except (LLMProviderError, StrategyValidationError) as exc:
        return render(
            request,
            "backtests/partials/parse_error.html",
            {"message": str(exc)},
        )

    return render(
        request,
        "backtests/partials/parse_result.html",
        {
            "strategy": strategy_to_dict(parsed),
            "parameters_json": json.dumps(parsed.parameters),
        },
    )


@login_required
def run_confirmed_backtest(request):
    form = ConfirmedStrategyForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "backtests/partials/parse_error.html",
            {"message": "Confirmed strategy parameters are invalid."},
            status=400,
        )

    parsed = parse_strategy_payload(form.cleaned_data)
    strategy = Strategy.objects.create(
        user=request.user,
        name=form.cleaned_data["name"],
        original_prompt="Confirmed strategy configuration",
        strategy_type=parsed.strategy_type,
        ticker=parsed.ticker,
        start_date=parsed.start_date,
        end_date=parsed.end_date,
        initial_cash=parsed.initial_cash,
        parameters_json=parsed.parameters,
        buy_rule=parsed.buy_rule,
        sell_rule=parsed.sell_rule,
    )
    run = BacktestRun.objects.create(
        user=request.user, strategy=strategy, status="pending"
    )

    try:
        price_data = load_price_data(parsed.ticker, parsed.start_date, parsed.end_date)
        output = run_backtest(parsed, price_data)
        BacktestResult.objects.create(
            backtest_run=run,
            equity_curve_json=output.equity_curve,
            metrics_json=output.metrics,
            **output.metrics,
        )
        run.status = "completed"
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at"])
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_message", "completed_at"])

    return redirect("result_detail", run_id=run.id)


@login_required
def history(request):
    runs = BacktestRun.objects.filter(user=request.user).select_related(
        "strategy", "result"
    )
    return render(request, "backtests/history.html", {"runs": runs})


@login_required
def result_detail(request, run_id):
    run = get_object_or_404(
        BacktestRun.objects.select_related("strategy", "result"),
        id=run_id,
        user=request.user,
    )
    return render(request, "backtests/result_detail.html", {"run": run})
