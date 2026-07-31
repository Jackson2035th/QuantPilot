from datetime import date

import pandas as pd
import yfinance as yf


class MarketDataError(RuntimeError):
    pass


def load_price_data(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    symbol = ticker.upper()
    try:
        # yfinance treats the end date as exclusive, matching its normal date API.
        frame = yf.download(
            symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=10,
        )
    except Exception as exc:
        raise MarketDataError(f"Market data request failed for {symbol}") from exc

    if frame is None or frame.empty:
        raise MarketDataError(f"No market data returned for {symbol}")

    if isinstance(frame.columns, pd.MultiIndex):
        # yfinance can return two header rows; the backtest only needs the price field names.
        frame.columns = frame.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = []
    for column in required:
        if column not in frame.columns:
            missing.append(column)

    if missing:
        raise MarketDataError(f"Market data missing columns: {', '.join(missing)}")

    # Extra provider columns are removed because the engine uses only OHLCV prices.
    result = frame[required].copy()
    # Use one predictable format before passing the prices into Backtrader.
    result.columns = ["open", "high", "low", "close", "volume"]
    result.index.name = "date"
    # Backtrader cannot calculate indicators from rows with missing prices.
    result = result.dropna()
    if result.empty:
        raise MarketDataError(f"No usable market data returned for {symbol}")
    return result
