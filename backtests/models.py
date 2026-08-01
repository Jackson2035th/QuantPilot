from django.conf import settings
from django.db import models


class Strategy(models.Model):
    # Strategy stores the reusable rules and input values chosen by the user.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    original_prompt = models.TextField()
    strategy_type = models.CharField(max_length=40)
    ticker = models.CharField(max_length=12)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_cash = models.DecimalField(max_digits=14, decimal_places=2)
    parameters_json = models.JSONField()
    buy_rule = models.TextField()
    sell_rule = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class BacktestRun(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # A run records one attempt, including failures that do not produce a result.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    strategy = models.ForeignKey(
        Strategy, on_delete=models.CASCADE, related_name="runs"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    data_source = models.CharField(max_length=40, default="yfinance")
    engine = models.CharField(max_length=40, default="backtrader")

    @property
    def data_source_label(self):
        return self.data_source


class BacktestResult(models.Model):
    # One run has at most one result; rerunning updates this same related row.
    backtest_run = models.OneToOneField(
        BacktestRun, on_delete=models.CASCADE, related_name="result"
    )
    # Percentage metrics are stored as decimals, for example 0.10 means 10%.
    total_return = models.FloatField()
    annualized_return = models.FloatField()
    max_drawdown = models.FloatField()
    number_of_trades = models.IntegerField()
    win_rate = models.FloatField()
    sharpe_ratio = models.FloatField()
    volatility = models.FloatField()
    profit_factor = models.FloatField()
    equity_curve_json = models.JSONField()
    metrics_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
