from __future__ import annotations

from dataclasses import dataclass, field
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    room: str
    feeitem_id: str
    auth_mode: str = "manual"
    synjones_auth: str | None = field(default=None, repr=False)
    login_username: str | None = None
    login_password: str | None = field(default=None, repr=False)
    login_device_token: str | None = field(default=None, repr=False)
    query_interval_minutes: int = 30
    database_path: str = "electricity.db"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def load_settings() -> Settings:
    load_dotenv()
    auth_mode = os.getenv("AUTH_MODE", "manual").strip().lower() or "manual"
    if auth_mode not in {"manual", "login"}:
        raise ValueError("AUTH_MODE must be manual or login")
    try:
        interval = int(os.getenv("QUERY_INTERVAL_MINUTES", "30"))
    except ValueError as exc:
        raise ValueError("QUERY_INTERVAL_MINUTES must be an integer") from exc
    if interval <= 0:
        raise ValueError("QUERY_INTERVAL_MINUTES must be positive")

    synjones_auth = _required_env("SYNJONES_AUTH") if auth_mode == "manual" else None
    login_username = _required_env("LOGIN_USERNAME") if auth_mode == "login" else None
    login_password = _required_env("LOGIN_PASSWORD") if auth_mode == "login" else None
    login_device_token = _required_env("LOGIN_DEVICE_TOKEN") if auth_mode == "login" else None

    return Settings(
        auth_mode=auth_mode,
        synjones_auth=synjones_auth,
        login_username=login_username,
        login_password=login_password,
        login_device_token=login_device_token,
        room=_required_env("ROOM"),
        feeitem_id=_required_env("FEEITEM_ID"),
        query_interval_minutes=interval,
        database_path=os.getenv("DATABASE_PATH", "electricity.db").strip() or "electricity.db",
    )
