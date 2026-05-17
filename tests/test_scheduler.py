import asyncio

import pytest

from electricitybill.scheduler import PollScheduler


class SlowService:
    def __init__(self):
        self.calls = 0
        self.release = asyncio.Event()

    async def refresh_once(self):
        self.calls += 1
        await self.release.wait()
        return {"status": "success"}


class CountingService:
    def __init__(self):
        self.calls = 0

    async def refresh_once(self):
        self.calls += 1
        return {"status": "success", "calls": self.calls}


@pytest.mark.asyncio
async def test_trigger_once_skips_when_refresh_already_running():
    service = SlowService()
    scheduler = PollScheduler(service, interval_seconds=60)

    first = asyncio.create_task(scheduler.trigger_once())
    await asyncio.sleep(0)

    skipped = await scheduler.trigger_once()
    service.release.set()
    await first

    assert skipped == {"status": "skipped", "message": "refresh already running"}
    assert service.calls == 1


@pytest.mark.asyncio
async def test_start_runs_immediate_refresh_and_stop_cleanly():
    service = CountingService()
    scheduler = PollScheduler(service, interval_seconds=60)

    scheduler.start()
    await asyncio.sleep(0)
    await scheduler.stop()

    assert service.calls == 1
