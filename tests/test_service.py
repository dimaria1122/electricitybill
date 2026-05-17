import pytest

from electricitybill.client import AuthError, QueryError
from electricitybill.service import RefreshService
from electricitybill.storage import Storage


class FakeClient:
    async def fetch_balance_payload(self):
        return {"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001 剩余金额:105.123571"}}}


class AuthFailingClient:
    async def fetch_balance_payload(self):
        raise AuthError("authentication failed bearer SECRET_TOKEN")


class QueryFailingClient:
    async def fetch_balance_payload(self):
        raise QueryError("network failed bearer SECRET_TOKEN")


class ParseFailingClient:
    async def fetch_balance_payload(self):
        return {"msg": "success", "code": 200, "map": {"showData": {"信息": "no balance here"}}}


class AuthThenSuccessClient:
    def __init__(self):
        self.fetch_calls = 0
        self.refresh_calls = 0

    async def fetch_balance_payload(self):
        self.fetch_calls += 1
        if self.fetch_calls == 1:
            raise AuthError("authentication failed bearer SECRET_TOKEN")
        return {"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001 剩余金额:104.500000"}}}

    async def refresh_auth(self):
        self.refresh_calls += 1
        return "bearer NEW_TOKEN"


class AuthRetryFailingClient:
    def __init__(self):
        self.fetch_calls = 0
        self.refresh_calls = 0

    async def fetch_balance_payload(self):
        self.fetch_calls += 1
        raise AuthError("authentication failed bearer SECRET_TOKEN")

    async def refresh_auth(self):
        self.refresh_calls += 1
        return "bearer NEW_TOKEN"


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
    assert result["message"] == "authentication failed"
    assert "SECRET_TOKEN" not in str(result)
    assert storage.latest_reading() is None
    assert storage.last_query_event()["message"] == "authentication failed"
    assert "SECRET_TOKEN" not in str(storage.last_query_event())


@pytest.mark.asyncio
async def test_refresh_service_records_query_error_without_leaking_details(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    service = RefreshService(client=QueryFailingClient(), storage=storage)

    result = await service.refresh_once()

    assert result == {"status": "error", "message": "balance query failed"}
    assert storage.latest_reading() is None
    assert storage.last_query_event()["status"] == "error"
    assert storage.last_query_event()["message"] == "balance query failed"
    assert "SECRET_TOKEN" not in str(result)
    assert "SECRET_TOKEN" not in str(storage.last_query_event())


@pytest.mark.asyncio
async def test_refresh_service_records_parse_error_without_raw_response_details(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    service = RefreshService(client=ParseFailingClient(), storage=storage)

    result = await service.refresh_once()

    assert result == {"status": "error", "message": "balance response could not be parsed"}
    assert storage.latest_reading() is None
    assert storage.last_query_event()["status"] == "error"
    assert storage.last_query_event()["message"] == "balance response could not be parsed"


@pytest.mark.asyncio
async def test_refresh_service_retries_once_after_auth_refresh(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    client = AuthThenSuccessClient()
    service = RefreshService(client=client, storage=storage)

    result = await service.refresh_once()

    assert result["status"] == "success"
    assert result["balance"] == 104.5
    assert client.fetch_calls == 2
    assert client.refresh_calls == 1
    assert storage.latest_reading()["balance"] == 104.5
    assert storage.last_query_event()["status"] == "success"


@pytest.mark.asyncio
async def test_refresh_service_records_safe_auth_error_after_retry_failure(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    client = AuthRetryFailingClient()
    service = RefreshService(client=client, storage=storage)

    result = await service.refresh_once()

    assert result == {"status": "auth_error", "message": "authentication failed"}
    assert client.fetch_calls == 2
    assert client.refresh_calls == 1
    assert storage.latest_reading() is None
    assert storage.last_query_event()["message"] == "authentication failed"
    assert "SECRET_TOKEN" not in str(result)
    assert "SECRET_TOKEN" not in str(storage.last_query_event())
