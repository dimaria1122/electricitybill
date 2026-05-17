import httpx
import pytest

from electricitybill.auth import LoginError, LoginTokenProvider, StaticTokenProvider


@pytest.mark.asyncio
async def test_static_token_provider_returns_configured_token():
    provider = StaticTokenProvider("bearer static-token")

    assert await provider.get_token() == "bearer static-token"
    assert await provider.refresh_token() == "bearer static-token"


def test_static_token_provider_repr_does_not_include_token():
    provider = StaticTokenProvider("bearer SECRET_TOKEN")

    assert "SECRET_TOKEN" not in repr(provider)
    assert "auth_token" not in repr(provider)


@pytest.mark.asyncio
async def test_login_token_provider_posts_expected_form_and_returns_bearer_token(httpx_mock):
    httpx_mock.add_response(json={"access_token": "ACCESS_TOKEN", "token_type": "bearer", "expires_in": 3600})
    provider = LoginTokenProvider(
        username="student-id",
        password="student-password",
        device_token="device-token",
    )

    token = await provider.get_token()

    request = httpx_mock.get_request()
    assert str(request.url) == "http://121.251.19.62/berserker-auth/oauth/token"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert request.headers["authorization"].startswith("Basic ")
    assert request.content == (
        b"username=student-id&password=student-password&grant_type=password&scope=all"
        b"&loginFrom=app&logintype=sno&device_token=device-token&synAccessSource=app"
    )
    assert token == "bearer ACCESS_TOKEN"


@pytest.mark.asyncio
async def test_login_token_provider_reuses_cached_token(httpx_mock):
    httpx_mock.add_response(json={"access_token": "ACCESS_TOKEN", "token_type": "bearer"})
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    first = await provider.get_token()
    second = await provider.get_token()

    assert first == "bearer ACCESS_TOKEN"
    assert second == "bearer ACCESS_TOKEN"
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_login_token_provider_refresh_token_forces_new_login(httpx_mock):
    httpx_mock.add_response(json={"access_token": "FIRST_TOKEN", "token_type": "bearer"})
    httpx_mock.add_response(json={"access_token": "SECOND_TOKEN", "token_type": "bearer"})
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    assert await provider.get_token() == "bearer FIRST_TOKEN"
    assert await provider.refresh_token() == "bearer SECOND_TOKEN"
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_login_token_provider_uses_bearer_when_token_type_missing(httpx_mock):
    httpx_mock.add_response(json={"access_token": "ACCESS_TOKEN"})
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    assert await provider.get_token() == "bearer ACCESS_TOKEN"


@pytest.mark.asyncio
async def test_login_token_provider_rejects_missing_access_token(httpx_mock):
    httpx_mock.add_response(json={"token_type": "bearer"})
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    with pytest.raises(LoginError, match="login failed"):
        await provider.get_token()


@pytest.mark.asyncio
async def test_login_token_provider_rejects_http_error_with_safe_message(httpx_mock):
    httpx_mock.add_response(status_code=401, json={"error": "bad credentials"})
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    with pytest.raises(LoginError, match="login failed") as exc_info:
        await provider.get_token()

    assert "student-password" not in str(exc_info.value)
    assert "bad credentials" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_login_token_provider_rejects_network_error_with_safe_message(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("network down"))
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    with pytest.raises(LoginError, match="login failed") as exc_info:
        await provider.get_token()

    assert "student-password" not in str(exc_info.value)
    assert "network down" not in str(exc_info.value)


def test_login_token_provider_repr_does_not_include_secrets():
    provider = LoginTokenProvider("student-id", "student-password", "device-token")

    assert "student-password" not in repr(provider)
    assert "device-token" not in repr(provider)
    assert "password" not in repr(provider)
    assert "device_token" not in repr(provider)
