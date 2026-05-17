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


def create_app(
    storage: Storage | None = None,
    refresh_service: Any | None = None,
    enable_scheduler: bool = True,
    scheduler: Any | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    settings = None
    if storage is None or refresh_service is None:
        settings = load_settings()
        storage = Storage(settings.database_path)
        storage.initialize()
        client = HuiXinYiXiaoClient(settings.synjones_auth, settings.room, settings.feeitem_id)
        refresh_service = RefreshService(client, storage)
    else:
        storage.initialize()

    if scheduler is None and enable_scheduler and settings is not None:
        from electricitybill.scheduler import PollScheduler

        scheduler = PollScheduler(refresh_service, settings.query_interval_minutes * 60)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if scheduler is not None:
            scheduler.start()
        yield
        if scheduler is not None:
            await scheduler.stop()

    app = FastAPI(title="Electricity Bill Monitor", lifespan=lifespan)
    static_dir = static_dir or Path(__file__).parent / "static"
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
        if scheduler is not None:
            return await scheduler.trigger_once()
        return await refresh_service.refresh_once()

    @app.get("/", response_model=None)
    def dashboard() -> FileResponse | dict[str, str]:
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {
            "status": "dashboard_not_available",
            "message": "Dashboard static files are not installed yet",
        }

    return app


def _create_module_app() -> FastAPI:
    try:
        return create_app()
    except ValueError as exc:
        fallback = FastAPI(title="Electricity Bill Monitor")

        @fallback.get("/")
        def setup_required() -> dict[str, str]:
            return {"status": "setup_required", "message": str(exc)}

        return fallback


app = _create_module_app()
