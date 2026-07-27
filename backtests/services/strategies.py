import backtrader as bt


class MovingAverageCrossoverStrategy(bt.Strategy):
    params = (("short_window", 20), ("long_window", 50))

    def __init__(self):
        short_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_window
        )
        long_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_window
        )
        self.crossover = bt.indicators.CrossOver(short_ma, long_ma)

    def next(self):
        # Buy when the short-term average moves above the long-term average.
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
        self.rsi = bt.indicators.RSI_Safe(
            self.data.close, period=self.params.rsi_period
        )

    def next(self):
        # RSI is a 0-100 score. A low score suggests the price has recently fallen a lot.
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
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period,
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        # Buy when the faster price trend crosses above the slower signal trend.
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.sell()
