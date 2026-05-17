from dataclasses import dataclass, field
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    synjones_auth: str = field(repr=False)
    room: str
    feeitem_id: str
    query_interval_minutes: int = 30
    database_path: str = "electricity.db"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def load_settings() -> Settings:
    load_dotenv()
    try:
        interval = int(os.getenv("QUERY_INTERVAL_MINUTES", "30"))
    except ValueError as exc:
        raise ValueError("QUERY_INTERVAL_MINUTES must be an integer") from exc
    if interval <= 0:
        raise ValueError("QUERY_INTERVAL_MINUTES must be positive")
    return Settings(
        synjones_auth=_required_env("SYNJONES_AUTH"),
        room=_required_env("ROOM"),
        feeitem_id=_required_env("FEEITEM_ID"),
        query_interval_minutes=interval,
        database_path=os.getenv("DATABASE_PATH", "electricity.db").strip() or "electricity.db",
    )
