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

## Local demonstration data

Create a separate local demo account with real historical prices from yfinance:

```bash
python manage.py seed_demo_data --username quantpilot_demo --password "<local-password>"
```

To rebuild only records explicitly labelled as QuantPilot demo data:

```bash
python manage.py seed_demo_data --username quantpilot_demo --password "<local-password>" --reset
```

The command creates 15 completed runs across five tickers and all three supported
strategy types, plus one controlled failure. It does not call DeepSeek, but it
downloads real historical data from yfinance and labels completed runs
`yfinance`. If yfinance data cannot be fetched, it stops before replacing existing
demo records. `--reset` preserves unlabelled personal records, including other
records owned by the same account.

## Disclaimer

QuantPilot is for historical backtesting and educational analysis only. It does not provide financial advice or live trading.
