import sqlite3

import electricitybill.storage as storage_module
from electricitybill.storage import Storage


def test_storage_methods_close_connections(tmp_path, monkeypatch):
    connections = []
    original_connect = storage_module.sqlite3.connect

    class TrackingConnection(sqlite3.Connection):
        close_count = 0

        def close(self):
            type(self).close_count += 1
            super().close()

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs, factory=TrackingConnection)
        connections.append(connection)
        return connection

    monkeypatch.setattr(storage_module.sqlite3, "connect", connect)

    storage = Storage(tmp_path / "electricity.db")

    storage.initialize()
    storage.add_reading(room="room-001", balance=105.12, display_text="first", recorded_at="2026-05-16T12:00:00+00:00")
    storage.list_readings()
    storage.latest_reading()
    storage.add_query_event(status="success", message="ok", recorded_at="2026-05-16T12:01:00+00:00")
    storage.last_query_event()

    assert TrackingConnection.close_count == len(connections)


def test_storage_inserts_and_lists_readings(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()

    storage.add_reading(room="room-001", balance=105.12, display_text="房间名称: room-001 剩余金额:105.12", recorded_at="2026-05-16T12:00:00+00:00")

    readings = storage.list_readings()
    assert len(readings) == 1
    assert readings[0]["room"] == "room-001"
    assert readings[0]["balance"] == 105.12


def test_storage_records_and_returns_last_event(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()

    storage.add_query_event(status="auth_error", message="token invalid", recorded_at="2026-05-16T12:00:00+00:00")
    storage.add_query_event(status="success", message="ok", recorded_at="2026-05-16T12:01:00+00:00")

    assert storage.last_query_event()["status"] == "success"


def test_storage_returns_latest_reading(tmp_path):
    storage = Storage(tmp_path / "electricity.db")
    storage.initialize()
    storage.add_reading(room="room-001", balance=105.12, display_text="first", recorded_at="2026-05-16T12:00:00+00:00")
    storage.add_reading(room="room-001", balance=104.90, display_text="second", recorded_at="2026-05-16T12:30:00+00:00")

    latest = storage.latest_reading()

    assert latest["balance"] == 104.90
    assert latest["display_text"] == "second"
