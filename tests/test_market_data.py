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

    with patch("backtests.services.market_data.yf.download", return_value=frame):
        result = load_price_data("aapl", date(2024, 1, 1), date(2024, 1, 5))

    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert result.index.name == "date"
    assert result.iloc[0]["close"] == 104.0


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
