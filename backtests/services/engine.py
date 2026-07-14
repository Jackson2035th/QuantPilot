from dataclasses import dataclass

import backtrader as bt
import pandas as pd

from .metrics import calculate_metrics
from .schema import ParsedStrategy
from .strategies import MovingAverageCrossoverStrategy


@dataclass(frozen=True)
class BacktestOutput:
    equity_curve: list[dict]
    trades: list[dict]
    metrics: dict


class EquityObserver(bt.Observer):
    lines = ("value",)

    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()


class TradeRecorder(bt.Analyzer):
    def start(self):
        self.trades = []

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append({"pnl": float(trade.pnlcomm)})

    def get_analysis(self):
        return self.trades


def run_backtest(strategy: ParsedStrategy, price_data: pd.DataFrame) -> BacktestOutput:
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(float(strategy.initial_cash))

    data = bt.feeds.PandasData(dataname=_to_backtrader_frame(price_data))
    cerebro.adddata(data)

    if strategy.strategy_type == "ma_crossover":
        cerebro.addstrategy(
            MovingAverageCrossoverStrategy,
            short_window=int(strategy.parameters["short_window"]),
            long_window=int(strategy.parameters["long_window"]),
        )
    else:
        raise ValueError(f"Unsupported strategy type for engine: {strategy.strategy_type}")

    cerebro.addobserver(EquityObserver)
    cerebro.addanalyzer(TradeRecorder, _name="trade_recorder")

    results = cerebro.run()
    result = results[0]

    equity_curve = _extract_equity_curve(result, price_data)
    trades = list(result.analyzers.trade_recorder.get_analysis())
    metrics = calculate_metrics(equity_curve, trades, float(strategy.initial_cash))

    return BacktestOutput(equity_curve=equity_curve, trades=trades, metrics=metrics)


def _to_backtrader_frame(price_data: pd.DataFrame) -> pd.DataFrame:
    frame = price_data.copy()
    frame.columns = ["open", "high", "low", "close", "volume"]
    return frame


def _extract_equity_curve(result, price_data: pd.DataFrame) -> list[dict]:
    values = list(result.observers.equityobserver.lines.value.array)
    dates = []
    for index in price_data.index:
        dates.append(index.date().isoformat())

    equity_curve = []
    for day, value in zip(dates, values):
        if value and value == value:
            equity_curve.append({"date": day, "value": float(value)})
    return equity_curve
