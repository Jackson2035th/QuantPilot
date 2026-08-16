import backtrader as bt


class MovingAverageCrossoverStrategy(bt.Strategy):
    params = (("short_window", 20), ("long_window", 50))

    def __init__(self):
        # The two averages smooth the same prices over short and long periods.
        short_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_window
        )
        long_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_window
        )
        # CrossOver becomes positive on an upward cross and negative on a downward cross.
        self.crossover = bt.indicators.CrossOver(short_ma, long_ma)

    def next(self):
        # Buy when the short-term average moves above the long-term average.
        # self.position stops duplicate entries. Without a custom sizer, Backtrader
        # uses one share per order rather than investing all available cash.
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.sell()


class RSIStrategy(bt.Strategy):
    params = (
        ("rsi_period", 14),
        ("oversold_threshold", 30),
        ("overbought_threshold", 70),
    )

    def __init__(self):
        # RSI_Safe avoids calculation errors when recent prices have no downward moves.
        self.rsi = bt.indicators.RSI_Safe(
            self.data.close, period=self.params.rsi_period
        )

    def next(self):
        # RSI is a 0-100 momentum score. A low value means recent losses were
        # stronger than recent gains; it does not by itself prove the stock is cheap.
        if not self.position and self.rsi < self.params.oversold_threshold:
            self.buy()
        elif self.position and self.rsi > self.params.overbought_threshold:
            self.sell()


class MACDStrategy(bt.Strategy):
    params = (
        ("fast_period", 12),
        ("slow_period", 26),
        ("signal_period", 9),
    )

    def __init__(self):
        # MACD compares a fast price trend with a slower price trend.
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period,
        )
        # The signal line smooths MACD so a crossing can be used as a trade rule.
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        # A positive crossing means MACD moved above its signal line. This describes
        # recent momentum, not a forecast that the price must continue rising.
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.sell()
