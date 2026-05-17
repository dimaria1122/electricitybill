import pytest

from electricitybill.config import Settings, load_settings


def test_settings_loads_required_environment(monkeypatch):
    monkeypatch.setenv("SYNJONES_AUTH", "bearer token-value")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")
    monkeypatch.setenv("QUERY_INTERVAL_MINUTES", "30")
    monkeypatch.setenv("DATABASE_PATH", "test.db")

    settings = load_settings()

    assert settings == Settings(
        synjones_auth="bearer token-value",
        room="room-001",
        feeitem_id="261",
        query_interval_minutes=30,
        database_path="test.db",
    )


def test_settings_repr_does_not_include_token(monkeypatch):
    monkeypatch.setenv("SYNJONES_AUTH", "bearer token-value")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")

    settings = load_settings()

    assert "token-value" not in repr(settings)
    assert "synjones_auth" not in repr(settings)


def test_settings_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("SYNJONES_AUTH", "")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")

    with pytest.raises(ValueError, match="SYNJONES_AUTH"):
        load_settings()


def test_settings_rejects_non_positive_interval(monkeypatch):
    monkeypatch.setenv("SYNJONES_AUTH", "bearer token-value")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")
    monkeypatch.setenv("QUERY_INTERVAL_MINUTES", "0")

    with pytest.raises(ValueError, match="QUERY_INTERVAL_MINUTES"):
        load_settings()


def test_settings_rejects_non_integer_interval_with_clear_message(monkeypatch):
    monkeypatch.setenv("SYNJONES_AUTH", "bearer token-value")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")
    monkeypatch.setenv("QUERY_INTERVAL_MINUTES", "not-an-int")

    with pytest.raises(ValueError, match="QUERY_INTERVAL_MINUTES must be an integer"):
        load_settings()
