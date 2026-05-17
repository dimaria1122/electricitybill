from __future__ import annotations

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
