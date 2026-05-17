# Electricity Bill Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI electricity-balance monitor that queries the verified HuiXinYiXiao endpoint every 30 minutes, stores readings in SQLite, and displays balance/usage trends in a browser dashboard.

**Architecture:** The app is a small Python package with focused modules for configuration, API client/parsing, SQLite storage, usage calculations, scheduling, and FastAPI routes. The dashboard is served from local static files and consumes JSON endpoints; secrets live only in `.env`.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, httpx, python-dotenv, SQLite, pytest, pytest-httpx, plain HTML/CSS/JavaScript with Chart.js CDN.

---

## File Structure

- Create: `requirements.txt` — runtime and test dependencies.
- Create: `.gitignore` — ignore local secrets, database, caches, and visual companion files.
- Create: `.env.example` — safe configuration template without secrets.
- Create: `README.md` — setup, token handling, run, and verification instructions.
- Create: `electricitybill/__init__.py` — package marker.
- Create: `electricitybill/config.py` — typed settings loaded from environment.
- Create: `electricitybill/parser.py` — parse HuiXinYiXiao JSON into a balance result.
- Create: `electricitybill/client.py` — call the electricity endpoint and classify failures.
- Create: `electricitybill/storage.py` — SQLite schema, inserts, reads, and status queries.
- Create: `electricitybill/metrics.py` — consumption and estimate calculations.
- Create: `electricitybill/service.py` — one refresh workflow that connects client, parser, and storage.
- Create: `electricitybill/scheduler.py` — non-overlapping background polling loop.
- Create: `electricitybill/app.py` — FastAPI app, API routes, startup/shutdown hooks, static dashboard.
- Create: `electricitybill/static/index.html` — local dashboard shell.
- Create: `electricitybill/static/styles.css` — dashboard styling.
- Create: `electricitybill/static/app.js` — fetch API data and render charts/metrics.
- Create: `tests/test_config.py` — settings tests.
- Create: `tests/test_parser.py` — parser tests.
- Create: `tests/test_client.py` — HTTP client tests.
- Create: `tests/test_storage.py` — SQLite tests.
- Create: `tests/test_metrics.py` — usage calculation tests.
- Create: `tests/test_service.py` — refresh workflow tests.
- Create: `tests/test_api.py` — FastAPI endpoint tests.

## Task 1: Project scaffolding and configuration

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `electricitybill/__init__.py`
- Create: `electricitybill/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Create dependency and safe config files**

Create `requirements.txt` with:

```text
fastapi
uvicorn[standard]
httpx
python-dotenv
pytest
pytest-httpx
```

Create `.gitignore` with:

```gitignore
.env
*.db
__pycache__/
.pytest_cache/
.venv/
.superpowers/
```

Create `.env.example` with:

```env
SYNJONES_AUTH=bearer paste_token_here
ROOM=your_authorized_room_id
FEEITEM_ID=261
QUERY_INTERVAL_MINUTES=30
DATABASE_PATH=electricity.db
```

Create empty `electricitybill/__init__.py`.

- [ ] **Step 2: Write failing settings tests**

Create `tests/test_config.py`:

```python
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


def test_settings_rejects_missing_token(monkeypatch):
    monkeypatch.delenv("SYNJONES_AUTH", raising=False)
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
```

- [ ] **Step 3: Run config tests and verify RED**

Run: `python -m pytest tests/test_config.py -v`

Expected: FAIL because `electricitybill.config` does not exist.

- [ ] **Step 4: Implement minimal settings loader**

Create `electricitybill/config.py`:

```python
from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    synjones_auth: str
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
    interval = int(os.getenv("QUERY_INTERVAL_MINUTES", "30"))
    if interval <= 0:
        raise ValueError("QUERY_INTERVAL_MINUTES must be positive")
    return Settings(
        synjones_auth=_required_env("SYNJONES_AUTH"),
        room=_required_env("ROOM"),
        feeitem_id=_required_env("FEEITEM_ID"),
        query_interval_minutes=interval,
        database_path=os.getenv("DATABASE_PATH", "electricity.db").strip() or "electricity.db",
    )
```

- [ ] **Step 5: Run config tests and verify GREEN**

Run: `python -m pytest tests/test_config.py -v`

Expected: 3 PASS.

## Task 2: Balance parser

**Files:**
- Create: `electricitybill/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_parser.py`:

```python
import pytest

from electricitybill.parser import BalanceParseError, ParsedBalance, parse_balance_response


def test_parse_balance_response_extracts_room_and_balance():
    payload = {
        "msg": "success",
        "code": 200,
        "map": {"showData": {"信息": "房间名称: room-001 剩余金额:105.123571"}},
    }

    result = parse_balance_response(payload)

    assert result == ParsedBalance(
        room="room-001",
        balance=105.123571,
        display_text="房间名称: room-001 剩余金额:105.123571",
    )


def test_parse_balance_response_rejects_missing_balance_pattern():
    payload = {"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001"}}}

    with pytest.raises(BalanceParseError, match="balance"):
        parse_balance_response(payload)


def test_parse_balance_response_rejects_error_code():
    payload = {"msg": "fail", "code": 500, "map": {}}

    with pytest.raises(BalanceParseError, match="unexpected"):
        parse_balance_response(payload)
```

- [ ] **Step 2: Run parser tests and verify RED**

Run: `python -m pytest tests/test_parser.py -v`

Expected: FAIL because `electricitybill.parser` does not exist.

- [ ] **Step 3: Implement parser**

Create `electricitybill/parser.py`:

```python
from dataclasses import dataclass
import re
from typing import Any


class BalanceParseError(Exception):
    pass


@dataclass(frozen=True)
class ParsedBalance:
    room: str
    balance: float
    display_text: str


BALANCE_RE = re.compile(r"房间名称:\s*(?P<room>\S+)\s+剩余金额:\s*(?P<balance>\d+(?:\.\d+)?)")


def parse_balance_response(payload: dict[str, Any]) -> ParsedBalance:
    if payload.get("code") != 200 or payload.get("msg") != "success":
        raise BalanceParseError("unexpected response status")
    try:
        display_text = payload["map"]["showData"]["信息"]
    except (KeyError, TypeError) as exc:
        raise BalanceParseError("missing display text") from exc
    match = BALANCE_RE.search(display_text)
    if not match:
        raise BalanceParseError("missing balance pattern")
    return ParsedBalance(
        room=match.group("room"),
        balance=float(match.group("balance")),
        display_text=display_text,
    )
```

- [ ] **Step 4: Run parser tests and verify GREEN**

Run: `python -m pytest tests/test_parser.py -v`

Expected: 3 PASS.

## Task 3: HuiXinYiXiao HTTP client

**Files:**
- Create: `electricitybill/client.py`
- Test: `tests/test_client.py`

- [ ] **Step 1: Write failing client tests**

Create `tests/test_client.py`:

```python
import pytest

from electricitybill.client import AuthError, HuiXinYiXiaoClient, QueryError


@pytest.mark.asyncio
async def test_client_posts_expected_form_and_auth_header(httpx_mock):
    httpx_mock.add_response(json={"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001 剩余金额:105.123571"}}})
    client = HuiXinYiXiaoClient(auth_token="bearer abc", room="room-001", feeitem_id="261")

    payload = await client.fetch_balance_payload()

    request = httpx_mock.get_request()
    assert request.url == "http://121.251.19.62/charge/feeitem/getThirdData"
    assert request.headers["synjones-auth"] == "bearer abc"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert request.content == b"feeitemid=261&type=IEC&level=1&room=room-001"
    assert payload["code"] == 200


@pytest.mark.asyncio
async def test_client_raises_auth_error_for_401(httpx_mock):
    httpx_mock.add_response(status_code=401, json={"msg": "缺失令牌，鉴权失败"})
    client = HuiXinYiXiaoClient(auth_token="bearer bad", room="room-001", feeitem_id="261")

    with pytest.raises(AuthError, match="authentication failed"):
        await client.fetch_balance_payload()


@pytest.mark.asyncio
async def test_client_raises_query_error_for_bad_json(httpx_mock):
    httpx_mock.add_response(text="not json")
    client = HuiXinYiXiaoClient(auth_token="bearer abc", room="room-001", feeitem_id="261")

    with pytest.raises(QueryError, match="JSON"):
        await client.fetch_balance_payload()
```

- [ ] **Step 2: Run client tests and verify RED**

Run: `python -m pytest tests/test_client.py -v`

Expected: FAIL because `electricitybill.client` does not exist.

- [ ] **Step 3: Implement client**

Create `electricitybill/client.py`:

```python
from typing import Any

import httpx


class QueryError(Exception):
    pass


class AuthError(QueryError):
    pass


class HuiXinYiXiaoClient:
    ENDPOINT = "http://121.251.19.62/charge/feeitem/getThirdData"

    def __init__(self, auth_token: str, room: str, feeitem_id: str, timeout_seconds: float = 10.0) -> None:
        self.auth_token = auth_token
        self.room = room
        self.feeitem_id = feeitem_id
        self.timeout_seconds = timeout_seconds

    async def fetch_balance_payload(self) -> dict[str, Any]:
        headers = {
            "synjones-auth": self.auth_token,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
        }
        data = {
            "feeitemid": self.feeitem_id,
            "type": "IEC",
            "level": "1",
            "room": self.room,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.ENDPOINT, headers=headers, data=data)
        except httpx.HTTPError as exc:
            raise QueryError("network error while querying balance") from exc
        if response.status_code in (401, 403):
            raise AuthError("authentication failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise QueryError("response was not valid JSON") from exc
        if response.status_code >= 400:
            raise QueryError(f"unexpected HTTP status {response.status_code}")
        return payload
```

- [ ] **Step 4: Run client tests and verify GREEN**

Run: `python -m pytest tests/test_client.py -v`

Expected: 3 PASS.

## Task 4: SQLite storage

**Files:**
- Create: `electricitybill/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_storage.py`:

```python
from electricitybill.storage import Storage


def test_storage_inserts_and_lists_readings(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()

    storage.add_reading(room="room-001", balance=105.12, display_text="房间名称: room-001 剩余金额:105.12", recorded_at="2026-05-16T12:00:00+00:00")

    readings = storage.list_readings()
    assert len(readings) == 1
    assert readings[0]["room"] == "room-001"
    assert readings[0]["balance"] == 105.12


def test_storage_records_and_returns_last_event(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()

    storage.add_query_event(status="auth_error", message="token invalid", recorded_at="2026-05-16T12:00:00+00:00")
    storage.add_query_event(status="success", message="ok", recorded_at="2026-05-16T12:01:00+00:00")

    assert storage.last_query_event()["status"] == "success"


def test_storage_returns_latest_reading(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    storage.add_reading(room="room-001", balance=105.12, display_text="first", recorded_at="2026-05-16T12:00:00+00:00")
    storage.add_reading(room="room-001", balance=104.90, display_text="second", recorded_at="2026-05-16T12:30:00+00:00")

    latest = storage.latest_reading()

    assert latest["balance"] == 104.90
    assert latest["display_text"] == "second"
```

- [ ] **Step 2: Run storage tests and verify RED**

Run: `python -m pytest tests/test_storage.py -v`

Expected: FAIL because `electricitybill.storage` does not exist.

- [ ] **Step 3: Implement storage**

Create `electricitybill/storage.py`:

```python
from pathlib import Path
import sqlite3
from typing import Any


class Storage:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS readings(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room TEXT NOT NULL,
                  balance REAL NOT NULL,
                  display_text TEXT NOT NULL,
                  recorded_at TEXT NOT NULL,
                  source TEXT NOT NULL DEFAULT 'api'
                );
                CREATE TABLE IF NOT EXISTS query_events(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  status TEXT NOT NULL,
                  message TEXT NOT NULL,
                  recorded_at TEXT NOT NULL
                );
                """
            )

    def add_reading(self, room: str, balance: float, display_text: str, recorded_at: str, source: str = "api") -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO readings(room, balance, display_text, recorded_at, source) VALUES (?, ?, ?, ?, ?)",
                (room, balance, display_text, recorded_at, source),
            )

    def list_readings(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM readings ORDER BY recorded_at ASC, id ASC").fetchall()
        return [dict(row) for row in rows]

    def latest_reading(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM readings ORDER BY recorded_at DESC, id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def add_query_event(self, status: str, message: str, recorded_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO query_events(status, message, recorded_at) VALUES (?, ?, ?)",
                (status, message, recorded_at),
            )

    def last_query_event(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM query_events ORDER BY recorded_at DESC, id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
```

- [ ] **Step 4: Run storage tests and verify GREEN**

Run: `python -m pytest tests/test_storage.py -v`

Expected: 3 PASS.

## Task 5: Metrics calculations

**Files:**
- Create: `electricitybill/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write failing metrics tests**

Create `tests/test_metrics.py`:

```python
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


def test_summarize_readings_handles_empty_history():
    summary = summarize_readings([])

    assert summary["current_balance"] is None
    assert summary["estimated_days_remaining"] is None
```

- [ ] **Step 2: Run metrics tests and verify RED**

Run: `python -m pytest tests/test_metrics.py -v`

Expected: FAIL because `electricitybill.metrics` does not exist.

- [ ] **Step 3: Implement metrics**

Create `electricitybill/metrics.py`:

```python
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
    ordered = sorted(readings, key=lambda item: item["recorded_at"])
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
```

- [ ] **Step 4: Run metrics tests and verify GREEN**

Run: `python -m pytest tests/test_metrics.py -v`

Expected: 3 PASS.

## Task 6: Refresh service workflow

**Files:**
- Create: `electricitybill/service.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_service.py`:

```python
import pytest

from electricitybill.client import AuthError
from electricitybill.service import RefreshService
from electricitybill.storage import Storage


class FakeClient:
    async def fetch_balance_payload(self):
        return {"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001 剩余金额:105.123571"}}}


class AuthFailingClient:
    async def fetch_balance_payload(self):
        raise AuthError("authentication failed")


@pytest.mark.asyncio
async def test_refresh_service_stores_successful_reading(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    service = RefreshService(client=FakeClient(), storage=storage)

    result = await service.refresh_once()

    assert result["status"] == "success"
    assert storage.latest_reading()["balance"] == 105.123571
    assert storage.last_query_event()["status"] == "success"


@pytest.mark.asyncio
async def test_refresh_service_records_auth_error_without_reading(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    service = RefreshService(client=AuthFailingClient(), storage=storage)

    result = await service.refresh_once()

    assert result["status"] == "auth_error"
    assert storage.latest_reading() is None
    assert storage.last_query_event()["message"] == "authentication failed"
```

- [ ] **Step 2: Run service tests and verify RED**

Run: `python -m pytest tests/test_service.py -v`

Expected: FAIL because `electricitybill.service` does not exist.

- [ ] **Step 3: Implement service**

Create `electricitybill/service.py`:

```python
from datetime import datetime, timezone
from typing import Any, Protocol

from electricitybill.client import AuthError, QueryError
from electricitybill.parser import BalanceParseError, parse_balance_response
from electricitybill.storage import Storage


class BalanceClient(Protocol):
    async def fetch_balance_payload(self) -> dict[str, Any]: ...


class RefreshService:
    def __init__(self, client: BalanceClient, storage: Storage) -> None:
        self.client = client
        self.storage = storage

    async def refresh_once(self) -> dict[str, Any]:
        recorded_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = await self.client.fetch_balance_payload()
            parsed = parse_balance_response(payload)
        except AuthError as exc:
            self.storage.add_query_event("auth_error", str(exc), recorded_at)
            return {"status": "auth_error", "message": str(exc)}
        except (QueryError, BalanceParseError) as exc:
            self.storage.add_query_event("error", str(exc), recorded_at)
            return {"status": "error", "message": str(exc)}
        self.storage.add_reading(parsed.room, parsed.balance, parsed.display_text, recorded_at)
        self.storage.add_query_event("success", "ok", recorded_at)
        return {"status": "success", "balance": parsed.balance, "room": parsed.room, "recorded_at": recorded_at}
```

- [ ] **Step 4: Run service tests and verify GREEN**

Run: `python -m pytest tests/test_service.py -v`

Expected: 2 PASS.

## Task 7: FastAPI app and endpoints

**Files:**
- Create: `electricitybill/app.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from electricitybill.app import create_app
from electricitybill.storage import Storage


class FakeRefreshService:
    async def refresh_once(self):
        return {"status": "success", "balance": 104.9}


def test_api_returns_status_and_readings(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    storage.add_reading("room-001", 105.0, "first", "2026-05-16T12:00:00+00:00")
    storage.add_query_event("success", "ok", "2026-05-16T12:00:00+00:00")
    app = create_app(storage=storage, refresh_service=FakeRefreshService(), enable_scheduler=False)

    client = TestClient(app)

    status = client.get("/api/status").json()
    readings = client.get("/api/readings").json()

    assert status["current_balance"] == 105.0
    assert status["last_query_status"] == "success"
    assert readings[0]["balance"] == 105.0


def test_api_refresh_triggers_service(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    app = create_app(storage=storage, refresh_service=FakeRefreshService(), enable_scheduler=False)

    client = TestClient(app)

    response = client.post("/api/refresh")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `python -m pytest tests/test_api.py -v`

Expected: FAIL because `electricitybill.app` does not exist.

- [ ] **Step 3: Implement FastAPI app without scheduler first**

Create `electricitybill/app.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from electricitybill.client import HuiXinYiXiaoClient
from electricitybill.config import load_settings
from electricitybill.metrics import summarize_readings
from electricitybill.service import RefreshService
from electricitybill.storage import Storage


def create_app(storage: Storage | None = None, refresh_service: Any | None = None, enable_scheduler: bool = True) -> FastAPI:
    if storage is None or refresh_service is None:
        settings = load_settings()
        storage = Storage(settings.database_path)
        storage.initialize()
        client = HuiXinYiXiaoClient(settings.synjones_auth, settings.room, settings.feeitem_id)
        refresh_service = RefreshService(client, storage)
    else:
        storage.initialize()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if enable_scheduler:
            await refresh_service.refresh_once()
        yield

    app = FastAPI(title="Electricity Bill Monitor", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/api/status")
    def api_status() -> dict[str, Any]:
        latest = storage.latest_reading()
        event = storage.last_query_event()
        summary = summarize_readings(storage.list_readings())
        return {
            "current_balance": latest["balance"] if latest else None,
            "last_updated": latest["recorded_at"] if latest else None,
            "last_query_status": event["status"] if event else "never",
            "last_query_message": event["message"] if event else "No query has run yet",
            "metrics": summary,
        }

    @app.get("/api/readings")
    def api_readings() -> list[dict[str, Any]]:
        return storage.list_readings()

    @app.post("/api/refresh")
    async def api_refresh() -> dict[str, Any]:
        return await refresh_service.refresh_once()

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    return app


app = create_app()
```

- [ ] **Step 4: Run API tests and verify GREEN**

Run: `python -m pytest tests/test_api.py -v`

Expected: 2 PASS.

## Task 8: Scheduler

**Files:**
- Create: `electricitybill/scheduler.py`
- Modify: `electricitybill/app.py`

- [ ] **Step 1: Add scheduler implementation**

Create `electricitybill/scheduler.py`:

```python
import asyncio
from typing import Protocol


class Refreshable(Protocol):
    async def refresh_once(self) -> dict: ...


class PollScheduler:
    def __init__(self, service: Refreshable, interval_seconds: float) -> None:
        self.service = service
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._stopped = asyncio.Event()

    async def trigger_once(self) -> dict:
        if self._lock.locked():
            return {"status": "skipped", "message": "refresh already running"}
        async with self._lock:
            return await self.service.refresh_once()

    async def _run(self) -> None:
        await self.trigger_once()
        while not self._stopped.is_set():
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                await self.trigger_once()

    def start(self) -> None:
        self._stopped.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            await self._task
```

- [ ] **Step 2: Wire scheduler into app lifespan**

Modify `electricitybill/app.py` so `create_app` computes settings once and starts `PollScheduler(refresh_service, settings.query_interval_minutes * 60)` when `enable_scheduler=True`. For injected tests with no settings, use no scheduler. The `lifespan` body should be:

```python
    scheduler = None
    if enable_scheduler and settings is not None:
        from electricitybill.scheduler import PollScheduler
        scheduler = PollScheduler(refresh_service, settings.query_interval_minutes * 60)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if scheduler is not None:
            scheduler.start()
        yield
        if scheduler is not None:
            await scheduler.stop()
```

- [ ] **Step 3: Run current tests after scheduler integration**

Run: `python -m pytest tests -v`

Expected: all tests pass.

## Task 9: Dashboard static files

**Files:**
- Create: `electricitybill/static/index.html`
- Create: `electricitybill/static/styles.css`
- Create: `electricitybill/static/app.js`

- [ ] **Step 1: Create dashboard HTML**

Create `electricitybill/static/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>寝室电费监控</title>
    <link rel="stylesheet" href="/static/styles.css" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  </head>
  <body>
    <main class="container">
      <header>
        <div>
          <p class="eyebrow">HuiXinYiXiao Monitor</p>
          <h1>寝室电费监控</h1>
        </div>
        <button id="refreshButton">立即刷新</button>
      </header>
      <section id="message" class="message">正在加载...</section>
      <section class="cards">
        <article><span>当前余额</span><strong id="currentBalance">--</strong></article>
        <article><span>最近 24 小时消耗</span><strong id="consumption24h">--</strong></article>
        <article><span>7 日日均消耗</span><strong id="average7d">--</strong></article>
        <article><span>预计还能用</span><strong id="daysRemaining">--</strong></article>
      </section>
      <section class="chart-card">
        <h2>余额曲线</h2>
        <canvas id="balanceChart"></canvas>
      </section>
      <section class="chart-card">
        <h2>每次变化</h2>
        <canvas id="deltaChart"></canvas>
      </section>
    </main>
    <script src="/static/app.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Create dashboard CSS**

Create `electricitybill/static/styles.css`:

```css
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7fb; color: #172033; }
.container { max-width: 1100px; margin: 0 auto; padding: 32px 18px; }
header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.eyebrow { color: #6b7280; margin: 0; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; }
h1 { margin: 4px 0 0; font-size: 32px; }
button { border: 0; border-radius: 12px; padding: 12px 18px; background: #f5a623; color: white; font-weight: 700; cursor: pointer; }
.message { margin: 22px 0; padding: 14px 16px; border-radius: 12px; background: #fff7e6; color: #8a5a00; }
.message.error { background: #fee2e2; color: #991b1b; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px; margin-bottom: 18px; }
article, .chart-card { background: white; border-radius: 18px; padding: 20px; box-shadow: 0 12px 30px rgba(15, 23, 42, .08); }
article span { display: block; color: #6b7280; margin-bottom: 8px; }
article strong { font-size: 28px; }
.chart-card { margin-top: 18px; }
canvas { max-height: 360px; }
```

- [ ] **Step 3: Create dashboard JavaScript**

Create `electricitybill/static/app.js`:

```javascript
let balanceChart;
let deltaChart;

function yuan(value) {
  return value === null || value === undefined ? "--" : `¥ ${Number(value).toFixed(2)}`;
}

function days(value) {
  return value === null || value === undefined ? "数据不足" : `${Number(value).toFixed(1)} 天`;
}

async function loadDashboard() {
  const [statusResponse, readingsResponse] = await Promise.all([
    fetch("/api/status"),
    fetch("/api/readings"),
  ]);
  const status = await statusResponse.json();
  const readings = await readingsResponse.json();
  const metrics = status.metrics;
  document.getElementById("currentBalance").textContent = yuan(metrics.current_balance);
  document.getElementById("consumption24h").textContent = yuan(metrics.last_24h_consumption);
  document.getElementById("average7d").textContent = yuan(metrics.avg_daily_consumption_7d);
  document.getElementById("daysRemaining").textContent = days(metrics.estimated_days_remaining);
  const message = document.getElementById("message");
  message.textContent = `状态：${status.last_query_status}；最后更新：${status.last_updated || "暂无"}`;
  message.classList.toggle("error", status.last_query_status === "auth_error");
  renderCharts(readings, metrics.deltas);
}

function renderCharts(readings, deltas) {
  const labels = readings.map((item) => new Date(item.recorded_at).toLocaleString());
  const balances = readings.map((item) => item.balance);
  const consumptions = deltas.map((item) => item.consumption ?? 0);
  if (balanceChart) balanceChart.destroy();
  if (deltaChart) deltaChart.destroy();
  balanceChart = new Chart(document.getElementById("balanceChart"), {
    type: "line",
    data: { labels, datasets: [{ label: "余额", data: balances, borderColor: "#f5a623", tension: 0.25 }] },
  });
  deltaChart = new Chart(document.getElementById("deltaChart"), {
    type: "bar",
    data: { labels, datasets: [{ label: "消耗/充值变化", data: consumptions, backgroundColor: "#60a5fa" }] },
  });
}

document.getElementById("refreshButton").addEventListener("click", async () => {
  await fetch("/api/refresh", { method: "POST" });
  await loadDashboard();
});

loadDashboard().catch((error) => {
  const message = document.getElementById("message");
  message.textContent = `加载失败：${error.message}`;
  message.classList.add("error");
});
```

- [ ] **Step 4: Run API tests after static files**

Run: `python -m pytest tests/test_api.py -v`

Expected: 2 PASS.

## Task 10: README and final verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# Electricity Bill Monitor

Local-only electricity balance monitor for one authorized HuiXinYiXiao dorm room.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill your current `SYNJONES_AUTH` token from Reqable. Do not commit `.env`.

## Run

```bash
uvicorn electricitybill.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Verify one query

Click `立即刷新` on the page, or wait for the startup query. If the token is invalid, the dashboard shows an auth error and you should refresh the token in `.env` and restart the server.

## Security

- Only query rooms you are authorized to query.
- The token stays in local `.env`.
- The app does not store your account password.
- The app does not automate payment or bypass app protections.
```

- [ ] **Step 2: Run full automated test suite**

Run: `python -m pytest tests -v`

Expected: all tests pass.

- [ ] **Step 3: Run app smoke test without real token**

Run: `python -m uvicorn electricitybill.app:app --host 127.0.0.1 --port 8000`

Expected: service starts. If `.env` is missing, create it from `.env.example` with a placeholder token to verify configuration loading, then use a real token for actual querying.

- [ ] **Step 4: Manual real-token verification**

With a real token in `.env`, run the app and click `立即刷新`.

Expected: `/api/status` shows `last_query_status: success`, `/api/readings` contains a balance near the current App value, and the dashboard does not show the token.

## Self-Review Notes

- Spec coverage: The plan covers local FastAPI runtime, manual token configuration, query/parsing, SQLite history, scheduler, dashboard metrics, token failure handling, and README usage instructions.
- Placeholder scan: No `TBD`, unbounded `TODO`, or unspecified error-handling placeholders remain.
- Type consistency: Module names, class names, and function signatures are consistent across tests and implementation tasks.
