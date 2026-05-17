from dataclasses import dataclass
import re
from typing import Any


class BalanceParseError(Exception):
    pass


@dataclass(frozen=True)
class ParsedBalance:
    room: str
    balance: float
    display_text: str


BALANCE_RE = re.compile(r"房间名称:\s*(?P<room>\S+)\s+剩余金额:\s*(?P<balance>\d+(?:\.\d+)?)")


def parse_balance_response(payload: dict[str, Any]) -> ParsedBalance:
    if payload.get("code") != 200 or payload.get("msg") != "success":
        raise BalanceParseError("unexpected response status")
    try:
        display_text = payload["map"]["showData"]["信息"]
    except (KeyError, TypeError) as exc:
        raise BalanceParseError("missing display text") from exc
    match = BALANCE_RE.search(display_text)
    if not match:
        raise BalanceParseError("missing balance pattern")
    return ParsedBalance(
        room=match.group("room"),
        balance=float(match.group("balance")),
        display_text=display_text,
    )
