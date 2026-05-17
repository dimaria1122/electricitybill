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
