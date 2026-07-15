# QuantPilot

QuantPilot is a Django-based LLM-assisted quantitative trading backtesting prototype for US stock data.

## MVP Scope

- Natural language strategy input
- Strict JSON strategy parsing through a DeepSeek-compatible LLM provider
- User confirmation before execution
- yfinance historical data retrieval
- Backtrader execution for MA Crossover, RSI, and MACD
- Metrics and Chart.js equity curve display
- Authenticated backtest history

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## Tests

```bash
pytest
```

## Disclaimer

QuantPilot is for historical backtesting and educational analysis only. It does not provide financial advice or live trading.
