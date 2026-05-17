from electricitybill.metrics import summarize_readings


def test_summarize_readings_calculates_positive_consumption_and_estimate():
    readings = [
        {"balance": 110.0, "recorded_at": "2026-05-15T12:00:00+00:00"},
        {"balance": 108.0, "recorded_at": "2026-05-16T00:00:00+00:00"},
        {"balance": 105.0, "recorded_at": "2026-05-16T12:00:00+00:00"},
    ]

    summary = summarize_readings(readings)

    assert summary["current_balance"] == 105.0
    assert summary["last_24h_consumption"] == 5.0
    assert summary["avg_daily_consumption_7d"] == 5.0
    assert summary["estimated_days_remaining"] == 21.0
    assert summary["deltas"][1]["consumption"] == 2.0


def test_summarize_readings_marks_recharge_as_zero_consumption():
    readings = [
        {"balance": 100.0, "recorded_at": "2026-05-16T00:00:00+00:00"},
        {"balance": 120.0, "recorded_at": "2026-05-16T12:00:00+00:00"},
    ]

    summary = summarize_readings(readings)

    assert summary["last_24h_consumption"] == 0.0
    assert summary["deltas"][1]["type"] == "recharge"


def test_summarize_readings_orders_timezone_aware_timestamps_chronologically():
    readings = [
        {"balance": 90.0, "recorded_at": "2026-05-16T08:00:00+08:00"},
        {"balance": 85.0, "recorded_at": "2026-05-16T01:00:00+00:00"},
    ]

    summary = summarize_readings(readings)

    assert summary["current_balance"] == 85.0
    assert summary["last_24h_consumption"] == 5.0


def test_summarize_readings_handles_empty_history():
    summary = summarize_readings([])

    assert summary["current_balance"] is None
    assert summary["estimated_days_remaining"] is None
