from datetime import datetime, timezone
from typing import Any, Protocol

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
            payload = await self.client.fetch_balance_payload()
            parsed = parse_balance_response(payload)
        except AuthError:
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
