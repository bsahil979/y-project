"""Save served forecasts before outcomes are known, then score observed closes."""
import argparse
import csv
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def timestamp(raw):
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Timestamps must include a timezone.")
    return value


def positive_price(raw):
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Prices must be positive and finite.")
    return value


def capture(api_url, ticker, horizon, output):
    ticker = ticker.strip().upper()
    url = f"{api_url.rstrip('/')}/forecast/{quote(ticker, safe='')}?horizon={horizon}"
    with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=120) as response:
        forecast = json.load(response)
    curve = forecast.get("forecast", [])
    if forecast.get("ticker") != ticker or [row["step"] for row in curve] != list(range(1, horizon + 1)):
        raise ValueError("The API did not return a complete visible forecast for this ticker.")
    positive_price(forecast["spot_price"])
    for row in curve:
        positive_price(row["predicted_price"])
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "forecast": forecast,
    }
    with output.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, allow_nan=False)


def score(record, sessions):
    forecast = record["forecast"]
    origin = date.fromisoformat(forecast["price_as_of"])
    recorded_at = timestamp(record["recorded_at"])
    horizon = len(forecast["forecast"])
    if not horizon:
        raise ValueError("This record has no visible forecast.")
    ordered = sorted(sessions, key=lambda row: date.fromisoformat(row["session_date"]))
    dates = [date.fromisoformat(row["session_date"]) for row in ordered]
    if len(dates) != len(set(dates)) or origin not in dates:
        raise ValueError("Actuals must include the forecast origin and unique session dates.")
    first = dates.index(origin) + 1
    window = ordered[first:first + horizon]
    if len(window) < horizon:
        raise ValueError(f"Need {horizon} observed trading sessions after {origin}, found {len(window)}.")
    close_times = [timestamp(row["close_at"]) for row in window]
    if close_times[0] <= recorded_at or any(a >= b for a, b in zip(close_times, close_times[1:])):
        raise ValueError("Closes must follow forecast capture and be in chronological order.")
    spot = positive_price(forecast["spot_price"])
    if not math.isclose(positive_price(ordered[first - 1]["close"]), spot, rel_tol=0.0001):
        raise ValueError("The origin close differs from the recorded close. Check the price basis.")
    actual = [positive_price(row["close"]) for row in window]
    prediction = [positive_price(row["predicted_price"]) for row in forecast["forecast"]]
    model_error = sum(abs(pred - close) for pred, close in zip(prediction, actual)) / horizon
    baseline_error = sum(abs(spot - close) for close in actual) / horizon

    def direction(price):
        return (price > spot) - (price < spot)

    return {
        "ticker": forecast["ticker"],
        "model_family": forecast.get("model_family"),
        "fallback_triggered": forecast.get("fallback_triggered"),
        "forecast_origin": str(origin),
        "last_actual_session": window[-1]["session_date"],
        "horizon_sessions": horizon,
        "model_mae_pct_of_spot": model_error / spot * 100,
        "last_close_mae_pct_of_spot": baseline_error / spot * 100,
        "terminal_direction_correct": direction(prediction[-1]) == direction(actual[-1]),
        "last_close_terminal_direction_correct": direction(spot) == direction(actual[-1]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record")
    record.add_argument("--api", required=True)
    record.add_argument("--ticker", required=True)
    record.add_argument("--horizon", type=int, default=30)
    record.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser("score")
    evaluate.add_argument("--record", type=Path, required=True)
    evaluate.add_argument("--actuals", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "record":
            if not 1 <= args.horizon <= 60:
                parser.error("horizon must be between 1 and 60")
            capture(args.api, args.ticker, args.horizon, args.output)
            print(args.output)
        else:
            with args.actuals.open(encoding="utf-8-sig", newline="") as handle:
                report = score(json.loads(args.record.read_text(encoding="utf-8")), list(csv.DictReader(handle)))
            print(json.dumps(report, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
