from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import get_user_profile
from backtests.models import BacktestResult, BacktestRun, Strategy
from backtests.services.engine import run_backtest
from backtests.services.market_data import MarketDataError, load_price_data
from backtests.services.schema import ParsedStrategy


DEMO_PREFIX = "[QuantPilot demo]"
START_DATE = date(2022, 1, 3)
END_DATE = date(2024, 12, 31)
INITIAL_CASH = 10_000.0

TICKERS = [
    {"ticker": "AAPL", "label": "Apple"},
    {"ticker": "MSFT", "label": "Microsoft"},
    {"ticker": "TSLA", "label": "Tesla"},
    {"ticker": "NVDA", "label": "NVIDIA"},
    {"ticker": "AMZN", "label": "Amazon"},
]

STRATEGIES = [
    {
        "type": "ma_crossover",
        "label": "MA Crossover",
        "parameters": {"short_window": 20, "long_window": 50},
        "buy_rule": "Buy when the 20-day moving average crosses above the 50-day average.",
        "sell_rule": "Sell when the 20-day moving average crosses below the 50-day average.",
    },
    {
        "type": "rsi",
        "label": "RSI",
        "parameters": {
            "rsi_period": 14,
            "oversold_threshold": 35,
            "overbought_threshold": 65,
        },
        "buy_rule": "Buy when the 14-day RSI falls below 35.",
        "sell_rule": "Sell when the 14-day RSI rises above 65.",
    },
    {
        "type": "macd",
        "label": "MACD",
        "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "buy_rule": "Buy when MACD crosses above its signal line.",
        "sell_rule": "Sell when MACD crosses below its signal line.",
    },
]


class Command(BaseCommand):
    help = "Create local demonstration backtests from real yfinance price data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="quantpilot_demo",
            help="Local account that will own the demonstration records.",
        )
        parser.add_argument(
            "--password",
            help=(
                "Local login password. Required when the account is first created; "
                "never stored by this command."
            ),
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Replace only records carrying the QuantPilot demo marker.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options.get("password")
        reset = options["reset"]
        if not username:
            raise CommandError("--username cannot be blank")

        self._ensure_reset_is_safe(username, reset)
        price_data_by_ticker = self._load_demo_price_data()

        with transaction.atomic():
            user, created = self._get_or_create_user(username, password)
            demo_strategies = Strategy.objects.filter(
                user=user,
                original_prompt__startswith=DEMO_PREFIX,
            )
            existing_count = demo_strategies.count()
            if existing_count and not reset:
                raise CommandError(
                    f"{existing_count} demo strategies already exist for {username}. "
                    "Run again with --reset to replace only labelled demo records."
                )
            if reset:
                demo_strategies.delete()

            if password and not created:
                user.set_password(password)
                user.save(update_fields=["password"])

            profile = get_user_profile(user)
            if not profile.has_completed_onboarding:
                profile.has_completed_onboarding = True
                profile.save(update_fields=["has_completed_onboarding"])

            completed_count = self._create_completed_runs(user, price_data_by_ticker)
            self._create_controlled_failure(user, completed_count + 1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {completed_count} completed and 1 controlled-failure "
                f"demo runs for {username}."
            )
        )
        self.stdout.write(
            "Completed runs use real historical price data downloaded from yfinance."
        )

    def _ensure_reset_is_safe(self, username, reset):
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if not user:
            return
        existing_count = Strategy.objects.filter(
            user=user,
            original_prompt__startswith=DEMO_PREFIX,
        ).count()
        if existing_count and not reset:
            raise CommandError(
                f"{existing_count} demo strategies already exist for {username}. "
                "Run again with --reset to replace only labelled demo records."
            )

    def _load_demo_price_data(self):
        price_data_by_ticker = {}
        for ticker_spec in TICKERS:
            ticker = ticker_spec["ticker"]
            try:
                price_data_by_ticker[ticker] = load_price_data(
                    ticker,
                    START_DATE,
                    END_DATE,
                )
            except MarketDataError as exc:
                raise CommandError(
                    f"Could not load yfinance data for {ticker}; no demo records were replaced."
                ) from exc
        return price_data_by_ticker

    def _get_or_create_user(self, username, password):
        User = get_user_model()
        try:
            return User.objects.get(username=username), False
        except User.DoesNotExist:
            if not password:
                raise CommandError(
                    "--password is required when creating the local demo account"
                )
            user = User.objects.create_user(
                username=username,
                email=f"{username}@example.invalid",
                password=password,
            )
            return user, True

    def _create_completed_runs(self, user, price_data_by_ticker):
        created = 0
        total = len(TICKERS) * len(STRATEGIES)
        for ticker_spec in TICKERS:
            price_data = price_data_by_ticker[ticker_spec["ticker"]]
            for strategy_spec in STRATEGIES:
                created += 1
                parsed = _build_parsed_strategy(ticker_spec, strategy_spec)
                output = run_backtest(parsed, price_data)
                strategy = Strategy.objects.create(
                    user=user,
                    name=(
                        f"Demo {created:02d} | {ticker_spec['ticker']} | "
                        f"{strategy_spec['label']}"
                    ),
                    original_prompt=(
                        f"{DEMO_PREFIX} Backtest {ticker_spec['label']} "
                        f"with the {strategy_spec['label']} strategy."
                    ),
                    strategy_type=parsed.strategy_type,
                    ticker=parsed.ticker,
                    start_date=parsed.start_date,
                    end_date=parsed.end_date,
                    initial_cash=parsed.initial_cash,
                    parameters_json=parsed.parameters,
                    buy_rule=parsed.buy_rule,
                    sell_rule=parsed.sell_rule,
                )
                recorded_at = timezone.now() - timedelta(days=total - created + 1)
                Strategy.objects.filter(pk=strategy.pk).update(
                    created_at=recorded_at,
                    updated_at=recorded_at,
                )
                run = BacktestRun.objects.create(
                    user=user,
                    strategy=strategy,
                    status="completed",
                    completed_at=recorded_at,
                    data_source="yfinance",
                    engine="backtrader",
                )
                BacktestRun.objects.filter(pk=run.pk).update(started_at=recorded_at)
                BacktestResult.objects.create(
                    backtest_run=run,
                    equity_curve_json=output.equity_curve,
                    metrics_json=output.metrics,
                    **output.metrics,
                )
        return created

    def _create_controlled_failure(self, user, sequence):
        strategy_spec = STRATEGIES[0]
        ticker_spec = TICKERS[0]
        parsed = _build_parsed_strategy(ticker_spec, strategy_spec)
        strategy = Strategy.objects.create(
            user=user,
            name=f"Demo {sequence:02d} | AAPL | Controlled data failure",
            original_prompt=(
                f"{DEMO_PREFIX} Demonstrate a safe market-data failure state."
            ),
            strategy_type=parsed.strategy_type,
            ticker=parsed.ticker,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            initial_cash=parsed.initial_cash,
            parameters_json=parsed.parameters,
            buy_rule=parsed.buy_rule,
            sell_rule=parsed.sell_rule,
        )
        recorded_at = timezone.now()
        run = BacktestRun.objects.create(
            user=user,
            strategy=strategy,
            status="failed",
            completed_at=recorded_at,
            error_message=(
                "Market data could not be loaded. Check the ticker and date range, "
                "then try again."
            ),
            data_source="yfinance",
            engine="backtrader",
        )
        BacktestRun.objects.filter(pk=run.pk).update(started_at=recorded_at)


def _build_parsed_strategy(ticker_spec, strategy_spec):
    return ParsedStrategy(
        strategy_type=strategy_spec["type"],
        ticker=ticker_spec["ticker"],
        start_date=START_DATE,
        end_date=END_DATE,
        initial_cash=INITIAL_CASH,
        parameters=dict(strategy_spec["parameters"]),
        buy_rule=strategy_spec["buy_rule"],
        sell_rule=strategy_spec["sell_rule"],
    )


