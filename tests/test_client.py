import pytest

from electricitybill.client import AuthError, HuiXinYiXiaoClient, QueryError


class FakeTokenProvider:
    def __init__(self, token="bearer abc"):
        self.token = token
        self.refresh_calls = 0

    async def get_token(self):
        return self.token

    async def refresh_token(self):
        self.refresh_calls += 1
        return self.token


@pytest.mark.asyncio
async def test_client_posts_expected_form_and_auth_header(httpx_mock):
    httpx_mock.add_response(json={"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001 剩余金额:105.123571"}}})
    client = HuiXinYiXiaoClient(token_provider=FakeTokenProvider("bearer abc"), room="room-001", feeitem_id="261")

    payload = await client.fetch_balance_payload()

    request = httpx_mock.get_request()
    assert str(request.url) == "http://121.251.19.62/charge/feeitem/getThirdData"
    assert request.headers["synjones-auth"] == "bearer abc"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert request.content == b"feeitemid=261&type=IEC&level=1&room=room-001"
    assert payload["code"] == 200


@pytest.mark.asyncio
async def test_client_raises_auth_error_for_401(httpx_mock):
    httpx_mock.add_response(status_code=401, json={"msg": "缺失令牌，鉴权失败"})
    client = HuiXinYiXiaoClient(token_provider=FakeTokenProvider("bearer bad"), room="room-001", feeitem_id="261")

    with pytest.raises(AuthError, match="authentication failed"):
        await client.fetch_balance_payload()


@pytest.mark.asyncio
async def test_client_raises_query_error_for_bad_json(httpx_mock):
    httpx_mock.add_response(text="not json")
    client = HuiXinYiXiaoClient(token_provider=FakeTokenProvider("bearer abc"), room="room-001", feeitem_id="261")

    with pytest.raises(QueryError, match="JSON"):
        await client.fetch_balance_payload()


@pytest.mark.asyncio
async def test_client_refresh_auth_delegates_to_token_provider():
    token_provider = FakeTokenProvider("bearer abc")
    client = HuiXinYiXiaoClient(token_provider=token_provider, room="room-001", feeitem_id="261")

    assert await client.refresh_auth() == "bearer abc"
    assert token_provider.refresh_calls == 1
