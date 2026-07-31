import json
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import get_user_profile
from .forms import ConfirmedStrategyForm, StrategyPromptForm
from .guide import GUIDE_CHECKLIST, GUIDE_EXAMPLES, GUIDE_GLOSSARY, GUIDE_STEPS
from .models import BacktestResult, BacktestRun, Strategy
from .presentation import (
    build_comparison_rows,
    build_dashboard_metric_cards,
    build_history_rows,
    build_metric_cards,
    build_takeaways,
)
from .queries import latest_completed_run_for
from .services.engine import run_backtest
from .services.llm import DeepSeekProvider, LLMProviderError
from .services.market_data import MarketDataError, load_price_data
from .services.schema import (
    StrategyValidationError,
    parse_strategy_payload,
    strategy_to_dict,
)


logger = logging.getLogger(__name__)


def landing(request):
    return render(request, "landing.html")


@login_required
def dashboard(request):
    # select_related() in the query helper makes the related strategy and result ready here.
    featured_run = latest_completed_run_for(request.user)
    profile = get_user_profile(request.user)
    return render(
        request,
        "backtests/dashboard.html",
        {
            "featured_run": featured_run,
            "featured_metric_cards": (
                build_dashboard_metric_cards(featured_run.result)
                if featured_run
                else []
            ),
            "takeaways": build_takeaways(featured_run.result) if featured_run else [],
            "show_onboarding": not profile.has_completed_onboarding,
            "guide_examples": GUIDE_EXAMPLES,
            "guide_steps": GUIDE_STEPS,
        },
    )


@login_required
@require_POST
def dashboard_ai_explanation(request):
    # This POST endpoint returns a small template fragment for the dashboard panel.
    featured_run = latest_completed_run_for(request.user)
    if not featured_run:
        return render(
            request,
            "backtests/partials/dashboard_ai_explanation.html",
            {"error": "There is no completed backtest available to explain yet."},
        )

    provider = DeepSeekProvider(
        settings.DEEPSEEK_API_KEY,
        settings.DEEPSEEK_BASE_URL,
        settings.DEEPSEEK_MODEL,
    )
    try:
        explanation = provider.explain_backtest(featured_run.strategy, featured_run.result)
    except LLMProviderError:
        return render(
            request,
            "backtests/partials/dashboard_ai_explanation.html",
            {"error": "Unable to generate an AI explanation right now."},
        )

    return render(
        request,
        "backtests/partials/dashboard_ai_explanation.html",
        {"explanation": explanation},
    )


@login_required
def strategy_input(request):
    prompt = request.GET.get("prompt", "")
    return render(
        request,
        "backtests/strategy_input.html",
        {
            "form": StrategyPromptForm(initial={"prompt": prompt}),
            "guide_examples": GUIDE_EXAMPLES,
            "guide_checklist": GUIDE_CHECKLIST,
        },
    )


def guide(request):
    return render(
        request,
        "backtests/guide.html",
        {
            "guide_examples": GUIDE_EXAMPLES,
            "guide_checklist": GUIDE_CHECKLIST,
            "guide_glossary": GUIDE_GLOSSARY,
            "guide_steps": GUIDE_STEPS,
        },
    )


@login_required
@require_POST
def complete_onboarding(request):
    profile = get_user_profile(request.user)
    profile.has_completed_onboarding = True
    profile.save(update_fields=["has_completed_onboarding"])
    return redirect("dashboard")


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

    # The model turns plain English into structured values; schema validation follows.
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


def _save_backtest_output(run, parsed):
    # New runs and reruns share one path so their status and errors stay consistent.
    try:
        price_data = load_price_data(parsed.ticker, parsed.start_date, parsed.end_date)
        output = run_backtest(parsed, price_data)
        # A rerun replaces its old result instead of creating a second result row.
        BacktestResult.objects.update_or_create(
            backtest_run=run,
            defaults={
                "equity_curve_json": output.equity_curve,
                "metrics_json": output.metrics,
                **output.metrics,
            },
        )
        run.status = "completed"
        run.error_message = ""
    except MarketDataError:
        logger.warning("Market data failed for backtest run %s", run.id, exc_info=True)
        run.status = "failed"
        run.error_message = (
            "Market data could not be loaded. Check the ticker and date range, then try again."
        )
    except Exception:
        logger.exception("Backtest run %s failed", run.id)
        run.status = "failed"
        run.error_message = "The backtest could not be completed. Review the parameters and try again."
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "error_message", "completed_at"])


def _update_strategy_from_parsed(strategy, parsed, name):
    # Copy all validated values back to the existing database object during an edit.
    strategy.name = name
    strategy.strategy_type = parsed.strategy_type
    strategy.ticker = parsed.ticker
    strategy.start_date = parsed.start_date
    strategy.end_date = parsed.end_date
    strategy.initial_cash = parsed.initial_cash
    strategy.parameters_json = parsed.parameters
    strategy.buy_rule = parsed.buy_rule
    strategy.sell_rule = parsed.sell_rule
    strategy.save(
        update_fields=[
            "name",
            "strategy_type",
            "ticker",
            "start_date",
            "end_date",
            "initial_cash",
            "parameters_json",
            "buy_rule",
            "sell_rule",
            "updated_at",
        ]
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

    # Validate the confirmed browser values again before saving or running them.
    parsed = parse_strategy_payload(form.cleaned_data)
    # Save the strategy and run first so a failed attempt still appears in History.
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

    _save_backtest_output(run, parsed)

    return redirect("result_detail", run_id=run.id)


@login_required
def history(request):
    # GET values keep searches shareable in the URL and survive a page refresh.
    query = request.GET.get("q", "").strip()
    ticker = request.GET.get("ticker", "").strip()
    strategy_type = request.GET.get("strategy_type", "").strip()
    selected_date = request.GET.get("date", "").strip()
    sort = request.GET.get("sort", "")
    sort_order = request.GET.get("order", "")
    return_sort_order = sort_order if sort == "total_return" and sort_order in {"asc", "desc"} else ""
    # select_related() fetches Strategy and Result in the same database query.
    runs = BacktestRun.objects.filter(user=request.user).select_related(
        "strategy", "result"
    )

    # Show only ticker and strategy type choices that exist in this user's history.
    tickers = list(
        runs.order_by("strategy__ticker")
        .values_list("strategy__ticker", flat=True)
        .distinct()
    )
    strategy_types = list(
        runs.order_by("strategy__strategy_type")
        .values_list("strategy__strategy_type", flat=True)
        .distinct()
    )

    # Every supplied filter narrows the same user-owned queryset.
    if query:
        runs = runs.filter(strategy__name__icontains=query)
    if ticker:
        runs = runs.filter(strategy__ticker=ticker)
    if strategy_type:
        runs = runs.filter(strategy__strategy_type=strategy_type)
    if selected_date:
        runs = runs.filter(completed_at__date=selected_date)
    if return_sort_order:
        # Runs without a result stay at the bottom of either return order.
        if return_sort_order == "asc":
            runs = runs.order_by(F("result__total_return").asc(nulls_last=True), "-id")
        else:
            runs = runs.order_by(F("result__total_return").desc(nulls_last=True), "-id")

    next_return_sort_order = {
        # Each click cycles: no sort -> high first -> low first -> no sort.
        "": "desc",
        "desc": "asc",
        "asc": "",
    }[return_sort_order]
    next_return_sort_query = urlencode(
        # Keep the active filters when the user changes only the return sorting.
        {
            "sort": "total_return",
            "order": next_return_sort_order,
            "q": query,
            "ticker": ticker,
            "strategy_type": strategy_type,
            "date": selected_date,
        }
    )

    return render(
        request,
        "backtests/history.html",
        {
            "history_rows": build_history_rows(runs),
            "query": query,
            "tickers": tickers,
            "strategy_types": strategy_types,
            "selected_ticker": ticker,
            "selected_strategy_type": strategy_type,
            "selected_date": selected_date,
            "has_filters": bool(query or ticker or strategy_type or selected_date),
            "return_sort_order": return_sort_order,
            "next_return_sort_query": next_return_sort_query,
            "next_return_sort_label": {
                "": "Sort total return from high to low",
                "desc": "Sort total return from low to high",
                "asc": "Clear total return sorting",
            }[return_sort_order],
        },
    )


@login_required
def compare_backtests(request):
    run_ids = []
    # Remove duplicate IDs but keep the order selected by the user.
    for value in request.GET.getlist("runs"):
        try:
            run_id = int(value)
        except ValueError:
            continue
        if run_id not in run_ids:
            run_ids.append(run_id)

    if not 2 <= len(run_ids) <= 4:
        return render(
            request,
            "backtests/compare_backtests.html",
            {
                "comparison_error": "Choose between 2 and 4 completed backtests to compare.",
            },
            status=400,
        )

    # This user and status filter is the permission boundary for comparisons.
    selected_runs = BacktestRun.objects.filter(
        user=request.user, status="completed", id__in=run_ids
    ).select_related("strategy", "result")
    runs_by_id = {run.id: run for run in selected_runs if hasattr(run, "result")}
    # An id__in database query does not promise to keep the submitted order.
    runs = [runs_by_id[run_id] for run_id in run_ids if run_id in runs_by_id]

    if len(runs) != len(run_ids):
        return render(
            request,
            "backtests/compare_backtests.html",
            {
                "comparison_error": "One or more selected backtests are unavailable. Choose completed backtests from your history.",
            },
            status=400,
        )

    # The browser receives raw daily values so it can draw all curves on one chart.
    comparison_series = [
        {
            "label": f"{run.strategy.name} ({run.strategy.ticker})",
            "points": run.result.equity_curve_json,
        }
        for run in runs
    ]
    return render(
        request,
        "backtests/compare_backtests.html",
        {
            "comparison_rows": build_comparison_rows(runs),
            "comparison_series": comparison_series,
        },
    )


@login_required
def edit_backtest(request, run_id):
    # Filtering by user prevents someone editing another account's run by changing the URL.
    run = get_object_or_404(
        BacktestRun.objects.select_related("strategy"),
        id=run_id,
        user=request.user,
    )
    strategy = run.strategy
    parameters_json = json.dumps(strategy.parameters_json)

    if request.method == "POST":
        form = ConfirmedStrategyForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "backtests/edit_backtest.html",
                {
                    "run": run,
                    "strategy": strategy,
                    "parameters_json": parameters_json,
                    "message": "Confirmed strategy parameters are invalid.",
                },
                status=400,
            )

        parsed = parse_strategy_payload(form.cleaned_data)
        _update_strategy_from_parsed(strategy, parsed, form.cleaned_data["name"])
        # Mark the existing run as pending before replacing its saved result.
        run.status = "pending"
        run.error_message = ""
        run.completed_at = None
        run.save(update_fields=["status", "error_message", "completed_at"])
        _save_backtest_output(run, parsed)
        return redirect("result_detail", run_id=run.id)

    return render(
        request,
        "backtests/edit_backtest.html",
        {
            "run": run,
            "strategy": strategy,
            "parameters_json": parameters_json,
        },
    )


@login_required
def delete_backtest(request, run_id):
    run = get_object_or_404(
        BacktestRun.objects.select_related("strategy"),
        id=run_id,
        user=request.user,
    )
    if request.method == "POST":
        # The run and its result are removed when their parent strategy is deleted.
        run.strategy.delete()
        return redirect("history")
    return redirect("history")


@login_required
def result_detail(request, run_id):
    # The same ownership check protects result pages from guessed run IDs.
    run = get_object_or_404(
        BacktestRun.objects.select_related("strategy", "result"),
        id=run_id,
        user=request.user,
    )
    metric_cards = []
    if run.status == "completed":
        metric_cards = build_metric_cards(run.result)
    return render(
        request,
        "backtests/result_detail.html",
        {"run": run, "metric_cards": metric_cards},
    )
