from django.contrib import admin

from .models import BacktestResult, BacktestRun, Strategy


admin.site.register(Strategy)
admin.site.register(BacktestRun)
admin.site.register(BacktestResult)
