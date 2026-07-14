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
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.sell()
