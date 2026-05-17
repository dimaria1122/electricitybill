import pytest

from electricitybill.parser import BalanceParseError, ParsedBalance, parse_balance_response


def test_parse_balance_response_extracts_room_and_balance():
    payload = {
        "msg": "success",
        "code": 200,
        "map": {"showData": {"信息": "房间名称: room-001 剩余金额:105.123571"}},
    }

    result = parse_balance_response(payload)

    assert result == ParsedBalance(
        room="room-001",
        balance=105.123571,
        display_text="房间名称: room-001 剩余金额:105.123571",
    )


def test_parse_balance_response_rejects_missing_balance_pattern():
    payload = {"msg": "success", "code": 200, "map": {"showData": {"信息": "房间名称: room-001"}}}

    with pytest.raises(BalanceParseError, match="balance"):
        parse_balance_response(payload)


def test_parse_balance_response_rejects_error_code():
    payload = {"msg": "fail", "code": 500, "map": {}}

    with pytest.raises(BalanceParseError, match="unexpected"):
        parse_balance_response(payload)
