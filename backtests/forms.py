import re
from datetime import date

from django import forms
from django.utils import timezone


STRATEGY_PATTERNS = {
    "ma_crossover": re.compile(r"\b(?:moving\s+average|ma\s+crossover)\b", re.IGNORECASE),
    "rsi": re.compile(r"\brsi\b", re.IGNORECASE),
    "macd": re.compile(r"\bmacd\b", re.IGNORECASE),
}
# Upper-case instructions and indicator names can look like stock symbols. Excluding
# them prevents prompts such as "BUY USING RSI" from passing the asset check.
NON_TICKER_ACRONYMS = {
    "BACKTEST",
    "BUY",
    "FROM",
    "MA",
    "MACD",
    "RSI",
    "SELL",
    "USD",
    "USING",
    "WITH",
}
TICKER_PATTERN = re.compile(r"\b[A-Z]{1,8}(?:\.[A-Z]{1,2})?\b")
COMPANY_WITH_MARKER_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9&.'-]{1,})\s+(?:stock|shares|company)\b",
    re.IGNORECASE,
)
COMPANY_AFTER_BACKTEST_PATTERN = re.compile(
    r"\bbacktest\s+([A-Z][A-Za-z0-9&.'-]{1,})\b"
)
NON_COMPANY_WORDS = {
    "a",
    "an",
    "any",
    "backtest",
    "buy",
    "sell",
    "stock",
    "the",
    "this",
    "using",
}
DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
CASH_PATTERN = re.compile(
    r"(?:\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars?)\b)",
    re.IGNORECASE,
)
STRICT_DATE_ERROR = (
    "Enter a valid date in YYYY-MM-DD format using a four-digit year, "
    "a month from 01 to 12, and a valid day."
)


class StrictISODateField(forms.DateField):
    def to_python(self, value):
        # Check the submitted text before Django converts it to a date. This keeps
        # local formats such as "Dec. 31, 2024" out of stored strategy data.
        if isinstance(value, str) and value.strip():
            value = value.strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise forms.ValidationError(STRICT_DATE_ERROR)
        try:
            return super().to_python(value)
        except forms.ValidationError as exc:
            raise forms.ValidationError(STRICT_DATE_ERROR) from exc


def _has_asset_reference(prompt: str) -> bool:
    # Prefer an explicit upper-case ticker. A company name is accepted only when
    # wording such as "Apple stock" makes the intended asset clear.
    tickers = {
        match.group(0)
        for match in TICKER_PATTERN.finditer(prompt)
        if match.group(0) not in NON_TICKER_ACRONYMS
    }
    if tickers:
        return True

    company_matches = list(COMPANY_WITH_MARKER_PATTERN.finditer(prompt))
    company_matches.extend(COMPANY_AFTER_BACKTEST_PATTERN.finditer(prompt))
    return any(
        match.group(1).lower() not in NON_COMPANY_WORDS for match in company_matches
    )


def _strategy_type(prompt: str) -> str | None:
    matches = [name for name, pattern in STRATEGY_PATTERNS.items() if pattern.search(prompt)]
    # More than one match is ambiguous; the user must choose one strategy.
    return matches[0] if len(matches) == 1 else None


def _has_explicit_parameters(prompt: str, strategy_type: str) -> bool:
    # Parameter counts differ by indicator. Requiring every value here prevents
    # the provider from silently choosing common defaults.
    if strategy_type == "ma_crossover":
        return len(re.findall(r"\b\d{1,3}\s*[- ]?day\b", prompt, re.IGNORECASE)) >= 2
    if strategy_type == "rsi":
        return all(
            pattern.search(prompt)
            for pattern in (
                re.compile(r"\brsi\s*\(\s*\d{1,3}\s*\)", re.IGNORECASE),
                re.compile(r"\b(?:below|under)\s+\d{1,2}\b", re.IGNORECASE),
                re.compile(r"\b(?:above|over)\s+\d{1,2}\b", re.IGNORECASE),
            )
        )
    return bool(
        re.search(
            r"\bmacd\s*(?:\(|with\s+|using\s+)?\s*\d{1,3}\s*[,/]\s*"
            r"\d{1,3}\s*[,/]\s*\d{1,3}\s*\)?",
            prompt,
            re.IGNORECASE,
        )
    )


class StrategyPromptForm(forms.Form):
    prompt = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        max_length=2000,
        error_messages={"required": "Enter a strategy description."},
    )

    def clean_prompt(self):
        prompt = self.cleaned_data["prompt"].strip()
        if len(prompt) < 20:
            raise forms.ValidationError("Enter a valid strategy description.")

        if not _has_asset_reference(prompt):
            raise forms.ValidationError("Add a US stock ticker or company name.")

        strategy_type = _strategy_type(prompt)
        if not strategy_type:
            raise forms.ValidationError(
                "Add one supported strategy: moving average crossover, RSI, or MACD."
            )

        if not _has_explicit_parameters(prompt, strategy_type):
            raise forms.ValidationError(
                "Add all strategy parameters instead of relying on automatic defaults."
            )

        prompt_lower = prompt.lower()
        if "buy" not in prompt_lower or "sell" not in prompt_lower:
            raise forms.ValidationError("Describe both the buy rule and the sell rule.")

        prompt_dates = DATE_PATTERN.findall(prompt)
        if len(prompt_dates) < 2:
            raise forms.ValidationError(
                "Add a historical start date and end date in YYYY-MM-DD format."
            )
        try:
            for prompt_date in prompt_dates:
                date.fromisoformat(prompt_date)
        except ValueError as exc:
            raise forms.ValidationError(STRICT_DATE_ERROR) from exc

        if not CASH_PATTERN.search(prompt):
            raise forms.ValidationError("Add the starting cash amount.")

        return prompt


class ConfirmedStrategyForm(forms.Form):
    name = forms.CharField(max_length=120)
    strategy_type = forms.CharField()
    ticker = forms.CharField()
    start_date = StrictISODateField()
    end_date = StrictISODateField()
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
        # Each strategy exposes a different group of editable numeric fields.
        parameter_names = {
            "ma_crossover": ("short_window", "long_window"),
            "rsi": ("rsi_period", "oversold_threshold", "overbought_threshold"),
            "macd": ("fast_period", "slow_period", "signal_period"),
        }.get(cleaned_data.get("strategy_type", "").strip().lower())

        if not parameter_names:
            return cleaned_data

        # Visible fields replace the hidden JSON when the user edits any of them.
        structured_parameters = {
            name: cleaned_data.get(name) for name in parameter_names
        }
        if any(value is not None for value in structured_parameters.values()):
            for name, value in structured_parameters.items():
                if value is None:
                    self.add_error(name, "Enter a value.")
            if not self.errors:
                cleaned_data["parameters"] = structured_parameters
        # The JSON fallback supports requests that do not use the visible parameter fields.
        elif not cleaned_data.get("parameters"):
            self.add_error("parameters", "Strategy parameters are required.")

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date >= end_date:
            self.add_error("end_date", "End date must be after the start date.")

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
