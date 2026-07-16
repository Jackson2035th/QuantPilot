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
    strategy_type = forms.CharField()
    ticker = forms.CharField()
    start_date = forms.DateField()
    end_date = forms.DateField()
    initial_cash = forms.DecimalField(min_value=1)
    parameters = forms.JSONField()
    buy_rule = forms.CharField(widget=forms.Textarea)
    sell_rule = forms.CharField(widget=forms.Textarea)

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
