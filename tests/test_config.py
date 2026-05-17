import pytest

from electricitybill.config import Settings, load_settings


@pytest.fixture(autouse=True)
def disable_dotenv_loading(monkeypatch):
    monkeypatch.setattr("electricitybill.config.load_dotenv", lambda: None)


def test_settings_loads_required_environment(monkeypatch):
    monkeypatch.setenv("SYNJONES_AUTH", "bearer token-value")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")
    monkeypatch.setenv("QUERY_INTERVAL_MINUTES", "30")
    monkeypatch.setenv("DATABASE_PATH", "test.db")

    settings = load_settings()

    assert settings == Settings(
        auth_mode="manual",
        synjones_auth="bearer token-value",
        login_username=None,
        login_password=None,
        login_device_token=None,
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


def test_settings_loads_login_mode(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "login")
    monkeypatch.setenv("LOGIN_USERNAME", "student-id")
    monkeypatch.setenv("LOGIN_PASSWORD", "student-password")
    monkeypatch.setenv("LOGIN_DEVICE_TOKEN", "device-token")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")

    settings = load_settings()

    assert settings.auth_mode == "login"
    assert settings.synjones_auth is None
    assert settings.login_username == "student-id"
    assert settings.login_password == "student-password"
    assert settings.login_device_token == "device-token"


@pytest.mark.parametrize(
    ("missing_name", "match"),
    [
        ("LOGIN_USERNAME", "LOGIN_USERNAME"),
        ("LOGIN_PASSWORD", "LOGIN_PASSWORD"),
        ("LOGIN_DEVICE_TOKEN", "LOGIN_DEVICE_TOKEN"),
    ],
)
def test_settings_rejects_missing_login_credentials(monkeypatch, missing_name, match):
    monkeypatch.setenv("AUTH_MODE", "login")
    monkeypatch.setenv("LOGIN_USERNAME", "student-id")
    monkeypatch.setenv("LOGIN_PASSWORD", "student-password")
    monkeypatch.setenv("LOGIN_DEVICE_TOKEN", "device-token")
    monkeypatch.setenv(missing_name, "")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")

    with pytest.raises(ValueError, match=match):
        load_settings()


def test_settings_rejects_invalid_auth_mode(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "invalid")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")

    with pytest.raises(ValueError, match="AUTH_MODE"):
        load_settings()


def test_settings_repr_does_not_include_login_secrets(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "login")
    monkeypatch.setenv("LOGIN_USERNAME", "student-id")
    monkeypatch.setenv("LOGIN_PASSWORD", "student-password")
    monkeypatch.setenv("LOGIN_DEVICE_TOKEN", "device-token")
    monkeypatch.setenv("ROOM", "room-001")
    monkeypatch.setenv("FEEITEM_ID", "261")

    settings = load_settings()

    assert "student-password" not in repr(settings)
    assert "device-token" not in repr(settings)
    assert "login_password" not in repr(settings)
    assert "login_device_token" not in repr(settings)
