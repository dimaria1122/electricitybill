from datetime import datetime, timedelta
from typing import Any


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _positive_consumption(readings: list[dict[str, Any]]) -> float:
    total = 0.0
    for previous, current in zip(readings, readings[1:]):
        diff = float(previous["balance"]) - float(current["balance"])
        if diff > 0:
            total += diff
    return round(total, 6)


def summarize_readings(readings: list[dict[str, Any]]) -> dict[str, Any]:
    if not readings:
        return {
            "current_balance": None,
            "last_24h_consumption": None,
            "avg_daily_consumption_7d": None,
            "estimated_days_remaining": None,
            "deltas": [],
        }
    ordered = sorted(readings, key=lambda item: _parse_time(item["recorded_at"]))
    latest = ordered[-1]
    latest_time = _parse_time(latest["recorded_at"])
    deltas: list[dict[str, Any]] = []
    for index, reading in enumerate(ordered):
        if index == 0:
            deltas.append({"recorded_at": reading["recorded_at"], "consumption": None, "type": "initial"})
            continue
        previous = ordered[index - 1]
        raw = float(previous["balance"]) - float(reading["balance"])
        deltas.append({
            "recorded_at": reading["recorded_at"],
            "consumption": round(raw, 6),
            "type": "usage" if raw >= 0 else "recharge",
        })
    last_24h = [reading for reading in ordered if _parse_time(reading["recorded_at"]) >= latest_time - timedelta(hours=24)]
    last_7d = [reading for reading in ordered if _parse_time(reading["recorded_at"]) >= latest_time - timedelta(days=7)]
    last_24h_consumption = _positive_consumption(last_24h)
    seven_day_consumption = _positive_consumption(last_7d)
    first_7d_time = _parse_time(last_7d[0]["recorded_at"])
    covered_days = max((latest_time - first_7d_time).total_seconds() / 86400, 1.0)
    avg_daily = round(seven_day_consumption / covered_days, 6) if len(last_7d) > 1 else None
    estimate = None
    if avg_daily and avg_daily > 0:
        estimate = round(float(latest["balance"]) / avg_daily, 2)
    return {
        "current_balance": float(latest["balance"]),
        "last_24h_consumption": last_24h_consumption,
        "avg_daily_consumption_7d": avg_daily,
        "estimated_days_remaining": estimate,
        "deltas": deltas,
    }
