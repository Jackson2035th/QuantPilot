from django import forms


class StrategyPromptForm(forms.Form):
    prompt = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), max_length=2000)


class ConfirmedStrategyForm(forms.Form):
    strategy_type = forms.CharField()
    ticker = forms.CharField()
    start_date = forms.DateField()
    end_date = forms.DateField()
    initial_cash = forms.DecimalField(min_value=1)
    parameters = forms.JSONField()
    buy_rule = forms.CharField(widget=forms.Textarea)
    sell_rule = forms.CharField(widget=forms.Textarea)
