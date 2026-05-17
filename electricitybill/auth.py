from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx


class LoginError(Exception):
    pass


class TokenProvider(Protocol):
    async def get_token(self) -> str: ...

    async def refresh_token(self) -> str: ...


@dataclass
class StaticTokenProvider:
    auth_token: str = field(repr=False)

    async def get_token(self) -> str:
        return self.auth_token

    async def refresh_token(self) -> str:
        return self.auth_token


@dataclass
class LoginTokenProvider:
    username: str
    password: str = field(repr=False)
    device_token: str = field(repr=False)
    timeout_seconds: float = 10.0

    ENDPOINT = "http://121.251.19.62/berserker-auth/oauth/token"
    CLIENT_AUTH = "Basic bW9iaWxlX3NlcnZpY2VfcGxhdGZvcm06bW9iaWxlX3NlcnZpY2VfcGxhdGZvcm1fc2VjcmV0"
    USER_AGENT = (
        "Mozilla/5.0 (Linux; Android 16; Mobile) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Version/4.0 Mobile Safari/537.36/Synjones-E-Campus/2.3.31"
    )

    def __post_init__(self) -> None:
        self._cached_token: str | None = None

    async def get_token(self) -> str:
        if self._cached_token is None:
            self._cached_token = await self._login()
        return self._cached_token

    async def refresh_token(self) -> str:
        self._cached_token = None
        return await self.get_token()

    async def _login(self) -> str:
        headers = {
            "Authorization": self.CLIENT_AUTH,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": self.USER_AGENT,
            "Origin": "http://121.251.19.62",
            "X-Requested-With": "com.synjones.mobilegroup.ECampus",
            "Referer": "http://121.251.19.62/plat/login?synAccessSource=app&loginFrom=app&type=logout",
        }
        data = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "scope": "all",
            "loginFrom": "app",
            "logintype": "sno",
            "device_token": self.device_token,
            "synAccessSource": "app",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.ENDPOINT, headers=headers, data=data)
        except httpx.HTTPError as exc:
            raise LoginError("login failed") from exc
        if response.status_code >= 400:
            raise LoginError("login failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise LoginError("login failed") from exc
        access_token = str(payload.get("access_token") or "").strip()
        if not access_token:
            raise LoginError("login failed")
        token_type = str(payload.get("token_type") or "bearer").strip() or "bearer"
        return f"{token_type.lower()} {access_token}"
