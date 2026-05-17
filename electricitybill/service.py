from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from electricitybill.auth import LoginError
from electricitybill.client import AuthError, QueryError
from electricitybill.parser import BalanceParseError, parse_balance_response
from electricitybill.storage import Storage


class BalanceClient(Protocol):
    async def fetch_balance_payload(self) -> dict[str, Any]: ...


AUTH_ERROR_MESSAGE = "authentication failed"
QUERY_ERROR_MESSAGE = "balance query failed"
PARSE_ERROR_MESSAGE = "balance response could not be parsed"


class RefreshService:
    def __init__(self, client: BalanceClient, storage: Storage) -> None:
        self.client = client
        self.storage = storage

    async def refresh_once(self) -> dict[str, Any]:
        recorded_at = datetime.now(timezone.utc).isoformat()
        try:
            parsed = await self._fetch_and_parse()
        except AuthError:
            retry_result = await self._retry_after_auth_error(recorded_at)
            if retry_result is not None:
                return retry_result
            self.storage.add_query_event("auth_error", AUTH_ERROR_MESSAGE, recorded_at)
            return {"status": "auth_error", "message": AUTH_ERROR_MESSAGE}
        except QueryError:
            self.storage.add_query_event("error", QUERY_ERROR_MESSAGE, recorded_at)
            return {"status": "error", "message": QUERY_ERROR_MESSAGE}
        except BalanceParseError:
            self.storage.add_query_event("error", PARSE_ERROR_MESSAGE, recorded_at)
            return {"status": "error", "message": PARSE_ERROR_MESSAGE}
        self.storage.add_reading(parsed.room, parsed.balance, parsed.display_text, recorded_at)
        self.storage.add_query_event("success", "ok", recorded_at)
        return {"status": "success", "balance": parsed.balance, "room": parsed.room, "recorded_at": recorded_at}

    async def _fetch_and_parse(self):
        payload = await self.client.fetch_balance_payload()
        return parse_balance_response(payload)

    async def _retry_after_auth_error(self, recorded_at: str) -> dict[str, Any] | None:
        refresh_auth = getattr(self.client, "refresh_auth", None)
        if refresh_auth is None:
            return None
        try:
            await refresh_auth()
            parsed = await self._fetch_and_parse()
        except AuthError:
            self.storage.add_query_event("auth_error", AUTH_ERROR_MESSAGE, recorded_at)
            return {"status": "auth_error", "message": AUTH_ERROR_MESSAGE}
        except LoginError:
            self.storage.add_query_event("auth_error", AUTH_ERROR_MESSAGE, recorded_at)
            return {"status": "auth_error", "message": AUTH_ERROR_MESSAGE}
        except QueryError:
            self.storage.add_query_event("error", QUERY_ERROR_MESSAGE, recorded_at)
            return {"status": "error", "message": QUERY_ERROR_MESSAGE}
        except BalanceParseError:
            self.storage.add_query_event("error", PARSE_ERROR_MESSAGE, recorded_at)
            return {"status": "error", "message": PARSE_ERROR_MESSAGE}
        self.storage.add_reading(parsed.room, parsed.balance, parsed.display_text, recorded_at)
        self.storage.add_query_event("success", "ok", recorded_at)
        return {"status": "success", "balance": parsed.balance, "room": parsed.room, "recorded_at": recorded_at}
