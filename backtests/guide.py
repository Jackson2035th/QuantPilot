GUIDE_EXAMPLES = [
    {
        "title": "Moving Average Crossover",
        "summary": "Buy when a short moving average rises above a long moving average.",
        "prompt": (
            "Backtest AAPL using a 50-day and 200-day moving average crossover "
            "from 2020-01-01 to 2024-12-31 with $10,000."
        ),
    },
    {
        "title": "RSI Reversal",
        "summary": "Buy after a stock becomes oversold and sell after it becomes overbought.",
        "prompt": (
            "Backtest TSLA using RSI(14). Buy below 30 and sell above 70 from "
            "2020-01-01 to 2024-12-31 with $10,000."
        ),
    },
    {
        "title": "MACD Crossover",
        "summary": "Buy and sell when the MACD line crosses its signal line.",
        "prompt": (
            "Backtest MSFT with MACD 12, 26, 9. Buy on a bullish crossover and "
            "sell on a bearish crossover from 2020-01-01 to 2024-12-31 with $10,000."
        ),
    },
]

GUIDE_CHECKLIST = [
    "A US stock ticker, such as AAPL or TSLA.",
    "A strategy or indicator, such as moving average, RSI, or MACD.",
    "When to buy and when to sell.",
    "A historical start date and end date.",
    "Starting cash for the simulated portfolio.",
]

GUIDE_STEPS = [
    (
        "Create a strategy",
        "Describe the stock, rules, dates, and starting cash in plain English.",
    ),
    (
        "Review parameters",
        "Check the parsed settings and adjust them before running the backtest.",
    ),
    (
        "Read results",
        "Compare return, drawdown, win rate, and other historical measures.",
    ),
]

GUIDE_GLOSSARY = [
    ("Ticker", "The short trading symbol for a company, such as AAPL for Apple."),
    ("Moving average", "An average price over a chosen number of trading days."),
    (
        "RSI",
        "A momentum indicator often used to identify overbought or oversold conditions.",
    ),
    ("MACD", "A momentum indicator that compares two moving averages."),
    ("Return", "The percentage gain or loss over the backtest period."),
    ("Maximum drawdown", "The largest peak-to-trough loss during the backtest."),
    ("Win rate", "The percentage of completed trades that made a profit."),
    ("Sharpe ratio", "A measure of return relative to historical volatility."),
    ("Backtest", "A simulation that applies rules to historical market prices."),
]
