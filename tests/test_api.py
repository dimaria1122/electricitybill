from fastapi.testclient import TestClient

from electricitybill.app import create_app
from electricitybill.storage import Storage


class FakeRefreshService:
    async def refresh_once(self):
        return {"status": "success", "balance": 104.9}


class CountingRefreshService:
    def __init__(self):
        self.calls = 0

    async def refresh_once(self):
        self.calls += 1
        return {"status": "success"}


class FakeScheduler:
    def __init__(self):
        self.triggered = False
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def trigger_once(self):
        self.triggered = True
        return {"status": "skipped", "message": "refresh already running"}


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


def test_api_refresh_uses_scheduler_when_present(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    service = CountingRefreshService()
    scheduler = FakeScheduler()
    app = create_app(
        storage=storage,
        refresh_service=service,
        enable_scheduler=True,
        scheduler=scheduler,
    )

    client = TestClient(app)

    response = client.post("/api/refresh")

    assert response.status_code == 200
    assert response.json() == {"status": "skipped", "message": "refresh already running"}
    assert scheduler.triggered is True
    assert service.calls == 0


def test_dashboard_route_is_safe_before_static_files_exist(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    app = create_app(
        storage=storage,
        refresh_service=FakeRefreshService(),
        enable_scheduler=False,
        static_dir=tmp_path / "missing-static",
    )

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "dashboard_not_available"
