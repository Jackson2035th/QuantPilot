from dataclasses import asdict, dataclass
from datetime import date


class StrategyValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedStrategy:
    strategy_type: str
    ticker: str
    start_date: date
    end_date: date
    initial_cash: float
    parameters: dict
    buy_rule: str
    sell_rule: str


SUPPORTED_STRATEGIES = {"ma_crossover", "rsi", "macd"}


def parse_strategy_payload(payload: dict) -> ParsedStrategy:
    required = [
        "strategy_type",
        "ticker",
        "start_date",
        "end_date",
        "initial_cash",
        "parameters",
        "buy_rule",
        "sell_rule",
    ]
    for field in required:
        if field not in payload:
            raise StrategyValidationError(f"Missing required field: {field}")

    strategy_type = str(payload["strategy_type"]).strip().lower()
    if strategy_type not in SUPPORTED_STRATEGIES:
        raise StrategyValidationError(f"Unsupported strategy type: {strategy_type}")

    ticker = str(payload["ticker"]).strip().upper()
    if not ticker or not ticker.replace(".", "").isalpha() or len(ticker) > 8:
        raise StrategyValidationError("Ticker must be a US stock symbol")

    try:
        start_date = date.fromisoformat(str(payload["start_date"]))
        end_date = date.fromisoformat(str(payload["end_date"]))
    except ValueError as exc:
        raise StrategyValidationError("Dates must use YYYY-MM-DD format") from exc
    if start_date >= end_date:
        raise StrategyValidationError("start_date must be before end_date")
    if start_date > date.today() or end_date > date.today():
        raise StrategyValidationError("Dates cannot be in the future")

    try:
        initial_cash = float(payload["initial_cash"])
    except (TypeError, ValueError) as exc:
        raise StrategyValidationError("initial_cash must be positive") from exc
    if initial_cash <= 0:
        raise StrategyValidationError("initial_cash must be positive")

    parameters = payload["parameters"]
    if not isinstance(parameters, dict):
        raise StrategyValidationError("parameters must be an object")

    _validate_parameters(strategy_type, parameters)
    buy_rule = _require_rule(payload, "buy_rule")
    sell_rule = _require_rule(payload, "sell_rule")

    return ParsedStrategy(
        strategy_type=strategy_type,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        parameters=parameters,
        buy_rule=buy_rule,
        sell_rule=sell_rule,
    )


def strategy_to_dict(strategy: ParsedStrategy) -> dict:
    data = asdict(strategy)
    data["start_date"] = strategy.start_date.isoformat()
    data["end_date"] = strategy.end_date.isoformat()
    return data


def _require_int(parameters: dict, name: str, min_value: int, max_value: int) -> int:
    if name not in parameters:
        raise StrategyValidationError(f"Missing parameter: {name}")
    try:
        value = int(parameters[name])
    except (TypeError, ValueError) as exc:
        raise StrategyValidationError(
            f"{name} must be between {min_value} and {max_value}"
        ) from exc
    if value < min_value or value > max_value:
        raise StrategyValidationError(
            f"{name} must be between {min_value} and {max_value}"
        )
    return value


def _require_rule(payload: dict, name: str) -> str:
    value = payload[name]
    if not isinstance(value, str):
        raise StrategyValidationError(f"{name} must be text")
    value = value.strip()
    if not value:
        raise StrategyValidationError(f"{name} cannot be empty")
    if len(value) > 500:
        raise StrategyValidationError(f"{name} must be 500 characters or fewer")
    return value


def _validate_parameters(strategy_type: str, parameters: dict) -> None:
    if strategy_type == "ma_crossover":
        short_window = _require_int(parameters, "short_window", 2, 250)
        long_window = _require_int(parameters, "long_window", 3, 400)
        if short_window >= long_window:
            raise StrategyValidationError("short_window must be less than long_window")
    elif strategy_type == "rsi":
        _require_int(parameters, "rsi_period", 2, 100)
        oversold = _require_int(parameters, "oversold_threshold", 1, 99)
        overbought = _require_int(parameters, "overbought_threshold", 1, 99)
        if oversold >= overbought:
            raise StrategyValidationError(
                "oversold_threshold must be less than overbought_threshold"
            )
    elif strategy_type == "macd":
        fast_period = _require_int(parameters, "fast_period", 2, 100)
        slow_period = _require_int(parameters, "slow_period", 3, 200)
        _require_int(parameters, "signal_period", 2, 100)
        if fast_period >= slow_period:
            raise StrategyValidationError("fast_period must be less than slow_period")
