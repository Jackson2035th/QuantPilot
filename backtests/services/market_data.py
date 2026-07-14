from datetime import date

import pandas as pd
import yfinance as yf


class MarketDataError(RuntimeError):
    pass


def load_price_data(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    symbol = ticker.upper()
    frame = yf.download(
        symbol,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        auto_adjust=False,
        progress=False,
    )

    if frame.empty:
        raise MarketDataError(f"No market data returned for {symbol}")

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = []
    for column in required:
        if column not in frame.columns:
            missing.append(column)

    if missing:
        raise MarketDataError(f"Market data missing columns: {', '.join(missing)}")

    result = frame[required].copy()
    result.columns = ["open", "high", "low", "close", "volume"]
    result.index.name = "date"
    return result.dropna()
