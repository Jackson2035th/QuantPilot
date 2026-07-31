from dataclasses import dataclass

import backtrader as bt
import pandas as pd

from .metrics import calculate_metrics
from .schema import ParsedStrategy
from .strategies import MACDStrategy, MovingAverageCrossoverStrategy, RSIStrategy


@dataclass(frozen=True)
class BacktestOutput:
    # Keep the chart data, trade list, and summary numbers together as one result.
    equity_curve: list[dict]
    trades: list[dict]
    metrics: dict


class EquityObserver(bt.Observer):
    # Backtrader calls next() automatically once for every row of market data.
    lines = ("value",)

    def next(self):
        # Save the account value after each trading day so the chart can show its journey.
        self.lines.value[0] = self._owner.broker.getvalue()


class TradeRecorder(bt.Analyzer):
    def start(self):
        self.trades = []

    def notify_trade(self, trade):
        # Backtrader calls this method whenever a trade changes state.
        if trade.isclosed:
            # Only closed trades have a final profit or loss.
            self.trades.append({"pnl": float(trade.pnlcomm)})

    def get_analysis(self):
        return self.trades


def run_backtest(strategy: ParsedStrategy, price_data: pd.DataFrame) -> BacktestOutput:
    # Cerebro is the Backtrader object that owns the cash, prices, and strategy.
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(float(strategy.initial_cash))

    # Backtrader reads the normalised price table one trading day at a time.
    data = bt.feeds.PandasData(dataname=_to_backtrader_frame(price_data))
    cerebro.adddata(data)

    # Only the parameters needed by the selected strategy are passed to Backtrader.
    if strategy.strategy_type == "ma_crossover":
        cerebro.addstrategy(
            MovingAverageCrossoverStrategy,
            short_window=int(strategy.parameters["short_window"]),
            long_window=int(strategy.parameters["long_window"]),
        )
    elif strategy.strategy_type == "rsi":
        cerebro.addstrategy(
            RSIStrategy,
            rsi_period=int(strategy.parameters["rsi_period"]),
            oversold_threshold=int(strategy.parameters["oversold_threshold"]),
            overbought_threshold=int(strategy.parameters["overbought_threshold"]),
        )
    elif strategy.strategy_type == "macd":
        cerebro.addstrategy(
            MACDStrategy,
            fast_period=int(strategy.parameters["fast_period"]),
            slow_period=int(strategy.parameters["slow_period"]),
            signal_period=int(strategy.parameters["signal_period"]),
        )
    else:
        raise ValueError(f"Unsupported strategy type for engine: {strategy.strategy_type}")

    # The observer records daily value; the analyzer records completed trades.
    cerebro.addobserver(EquityObserver)
    cerebro.addanalyzer(TradeRecorder, _name="trade_recorder")

    results = cerebro.run()
    # This engine adds one strategy, so the first result is the complete run.
    result = results[0]

    equity_curve = _extract_equity_curve(result, price_data)
    trades = list(result.analyzers.trade_recorder.get_analysis())
    metrics = calculate_metrics(equity_curve, trades, float(strategy.initial_cash))

    return BacktestOutput(equity_curve=equity_curve, trades=trades, metrics=metrics)


def _to_backtrader_frame(price_data: pd.DataFrame) -> pd.DataFrame:
    # Backtrader expects these exact lower-case column names and this order.
    frame = price_data.copy()
    frame.columns = ["open", "high", "low", "close", "volume"]
    return frame


def _extract_equity_curve(result, price_data: pd.DataFrame) -> list[dict]:
    values = list(result.observers.equityobserver.lines.value.array)
    dates = []
    for index in price_data.index:
        dates.append(index.date().isoformat())

    equity_curve = []
    # Pair each recorded account value with the matching market date.
    for day, value in zip(dates, values):
        # A missing value is ignored; it cannot be plotted as a useful account balance.
        if value and value == value:
            equity_curve.append({"date": day, "value": float(value)})
    return equity_curve
