from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from backtests.services.market_data import MarketDataError, load_price_data


def test_load_price_data_normalizes_columns():
    frame = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
            "Volume": [1000000],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )

    with patch("backtests.services.market_data.yf.download", return_value=frame) as download:
        result = load_price_data("aapl", date(2024, 1, 1), date(2024, 1, 5))

    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert result.index.name == "date"
    assert result.iloc[0]["close"] == 104.0
    assert download.call_args.kwargs["timeout"] == 10
    assert download.call_args.kwargs["threads"] is False


def test_load_price_data_rejects_empty_response():
    with patch(
        "backtests.services.market_data.yf.download", return_value=pd.DataFrame()
    ):
        with pytest.raises(MarketDataError, match="No market data returned"):
            load_price_data("AAPL", date(2024, 1, 1), date(2024, 1, 5))


def test_load_price_data_rejects_missing_columns():
    frame = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )

    with patch("backtests.services.market_data.yf.download", return_value=frame):
        with pytest.raises(MarketDataError, match="Market data missing columns"):
            load_price_data("AAPL", date(2024, 1, 1), date(2024, 1, 5))


def test_load_price_data_wraps_download_errors():
    with patch(
        "backtests.services.market_data.yf.download",
        side_effect=RuntimeError("internal downloader detail"),
    ):
        with pytest.raises(MarketDataError, match="Market data request failed for AAPL"):
            load_price_data("AAPL", date(2024, 1, 1), date(2024, 1, 5))


def test_load_price_data_rejects_rows_with_no_usable_values():
    frame = pd.DataFrame(
        {
            "Open": [None],
            "High": [None],
            "Low": [None],
            "Close": [None],
            "Volume": [None],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )

    with patch("backtests.services.market_data.yf.download", return_value=frame):
        with pytest.raises(MarketDataError, match="No usable market data"):
            load_price_data("AAPL", date(2024, 1, 1), date(2024, 1, 5))


def test_load_price_data_reads_real_yfinance_history():
    result = load_price_data("AAPL", date(2024, 1, 2), date(2024, 1, 12))

    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert result.index.name == "date"
    assert len(result) >= 5
    assert result["close"].notna().all()
