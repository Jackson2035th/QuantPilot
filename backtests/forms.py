from django import forms
from django.utils import timezone


STRATEGY_PROMPT_KEYWORDS = {
    "aapl",
    "apple",
    "backtest",
    "buy",
    "cash",
    "crossover",
    "macd",
    "market",
    "moving",
    "rsi",
    "sell",
    "shares",
    "stock",
    "strategy",
    "tesla",
    "ticker",
    "trade",
    "trading",
}


class StrategyPromptForm(forms.Form):
    prompt = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        max_length=2000,
        error_messages={"required": "Enter a strategy description."},
    )

    def clean_prompt(self):
        prompt = self.cleaned_data["prompt"].strip()
        prompt_lower = prompt.lower()
        has_strategy_keyword = any(
            keyword in prompt_lower for keyword in STRATEGY_PROMPT_KEYWORDS
        )
        if len(prompt) < 20 or not has_strategy_keyword:
            raise forms.ValidationError("Enter a valid strategy description.")
        return prompt


class ConfirmedStrategyForm(forms.Form):
    name = forms.CharField(max_length=120)
    strategy_type = forms.CharField()
    ticker = forms.CharField()
    start_date = forms.DateField()
    end_date = forms.DateField()
    initial_cash = forms.DecimalField(min_value=1)
    parameters = forms.JSONField(required=False)
    short_window = forms.IntegerField(required=False)
    long_window = forms.IntegerField(required=False)
    rsi_period = forms.IntegerField(required=False)
    oversold_threshold = forms.IntegerField(required=False)
    overbought_threshold = forms.IntegerField(required=False)
    fast_period = forms.IntegerField(required=False)
    slow_period = forms.IntegerField(required=False)
    signal_period = forms.IntegerField(required=False)
    buy_rule = forms.CharField(widget=forms.Textarea)
    sell_rule = forms.CharField(widget=forms.Textarea)

    def clean(self):
        cleaned_data = super().clean()
        parameter_names = {
            "ma_crossover": ("short_window", "long_window"),
            "rsi": ("rsi_period", "oversold_threshold", "overbought_threshold"),
            "macd": ("fast_period", "slow_period", "signal_period"),
        }.get(cleaned_data.get("strategy_type", "").strip().lower())

        if not parameter_names:
            return cleaned_data

        structured_parameters = {
            name: cleaned_data.get(name) for name in parameter_names
        }
        if any(value is not None for value in structured_parameters.values()):
            for name, value in structured_parameters.items():
                if value is None:
                    self.add_error(name, "Enter a value.")
            if not self.errors:
                cleaned_data["parameters"] = structured_parameters
        elif not cleaned_data.get("parameters"):
            self.add_error("parameters", "Strategy parameters are required.")

        return cleaned_data

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]
        if start_date > timezone.localdate():
            raise forms.ValidationError("Date cannot be in the future.")
        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data["end_date"]
        if end_date > timezone.localdate():
            raise forms.ValidationError("Date cannot be in the future.")
        return end_date
