import asyncio
import json
import time

import pytest
from fastapi import HTTPException

from src.core.runtime_supervisor import RuntimeSupervisor
from src.symbol_runtime_control import build_symbol_command
from src.telegram_panel.backend.routes import runtime as runtime_routes
from src.telegram_panel.backend.routes import trades as trade_routes


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_runtime_status_missing_is_unavailable(tmp_path, monkeypatch):
    status_path = tmp_path / "runtime_status.json"
    command_path = tmp_path / "runtime_command.json"
    monkeypatch.setattr(runtime_routes, "STATUS_PATH", status_path)
    monkeypatch.setattr(runtime_routes, "COMMAND_PATH", command_path)

    status = runtime_routes._normalize_status(runtime_routes._read_json(status_path))

    assert status["state"] == "unavailable"
    assert status["control_enabled"] is False
    assert status["stale"] is True


def test_runtime_status_stale_disables_control(tmp_path, monkeypatch):
    status_path = tmp_path / "runtime_status.json"
    command_path = tmp_path / "runtime_command.json"
    monkeypatch.setattr(runtime_routes, "STATUS_PATH", status_path)
    monkeypatch.setattr(runtime_routes, "COMMAND_PATH", command_path)
    monkeypatch.setattr(runtime_routes, "STATUS_STALE_AFTER_SECONDS", 1)
    _write_json(status_path, {
        "state": "running",
        "control_enabled": True,
        "updated_at_ts": time.time() - 10,
    })

    status = runtime_routes._normalize_status(runtime_routes._read_json(status_path))

    assert status["state"] == "running"
    assert status["control_enabled"] is False
    assert status["stale"] is True


def test_runtime_command_is_written_when_supervisor_is_fresh(tmp_path, monkeypatch):
    status_path = tmp_path / "runtime_status.json"
    command_path = tmp_path / "runtime_command.json"
    monkeypatch.setattr(runtime_routes, "STATUS_PATH", status_path)
    monkeypatch.setattr(runtime_routes, "COMMAND_PATH", command_path)
    _write_json(status_path, {
        "state": "running",
        "control_enabled": True,
        "updated_at_ts": time.time(),
    })

    result = asyncio.run(runtime_routes.enqueue_runtime_command(
        "restart",
        {"user": {"id": 12345}},
    ))

    command = json.loads(command_path.read_text(encoding="utf-8"))
    assert result["status"] == "queued"
    assert command["action"] == "restart"
    assert command["requested_by"] == "telegram:12345"


def test_runtime_command_rejects_unavailable_supervisor(tmp_path, monkeypatch):
    status_path = tmp_path / "runtime_status.json"
    command_path = tmp_path / "runtime_command.json"
    monkeypatch.setattr(runtime_routes, "STATUS_PATH", status_path)
    monkeypatch.setattr(runtime_routes, "COMMAND_PATH", command_path)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(runtime_routes.enqueue_runtime_command("start", {"user": {"id": 1}}))

    assert exc.value.status_code == 409


def test_supervisor_ignores_already_seen_command(tmp_path, monkeypatch):
    supervisor = RuntimeSupervisor(
        command_path=tmp_path / "runtime_command.json",
        status_path=tmp_path / "runtime_status.json",
        start_on_boot=False,
    )
    supervisor.last_command_id = "same-command"
    calls = []
    monkeypatch.setattr(supervisor, "start_runtime", lambda source="manual": calls.append(source))

    supervisor._handle_command({
        "id": "same-command",
        "action": "start",
        "requested_by": "test",
    })

    assert calls == []


def test_symbol_runtime_command_payload_normalizes_symbol():
    command = build_symbol_command("restart", symbol="BTC-USDT", instance_id="BTC_MACDX", requested_by="test")

    assert command["action"] == "restart"
    assert command["symbol"] == "BTCUSDT"
    assert command["instance_id"] == "btc_macdx"
    assert command["requested_by"] == "test"


def test_symbol_runtime_command_payload_accepts_instance_ids():
    command = build_symbol_command("restart", instance_ids=["BTC_MACDX", "eth_hybrid"], requested_by="test")

    assert command["action"] == "restart"
    assert command["instance_ids"] == ["btc_macdx", "eth_hybrid"]


class _JsonRequest:
    def __init__(self, data):
        self._data = data

    async def json(self):
        return self._data


def test_symbol_runtime_route_writes_command(monkeypatch):
    calls = []

    def fake_write_symbol_command(action, **kwargs):
        calls.append((action, kwargs))
        return {
            "id": "cmd",
            "action": action,
            "requested_by": kwargs["requested_by"],
            "requested_at": "now",
            "requested_at_ts": 1,
            "instance_id": kwargs["instance_id"],
        }

    monkeypatch.setattr(runtime_routes, "write_symbol_command", fake_write_symbol_command)

    result = asyncio.run(runtime_routes.enqueue_symbol_runtime_command(
        "restart",
        _JsonRequest({"instance_id": "btc_macdx", "symbol": "BTCUSDT"}),
        {"user": {"id": 12345}},
    ))

    assert result["status"] == "queued"
    assert calls == [(
        "restart",
        {
            "requested_by": "telegram:12345",
            "symbol": "BTCUSDT",
            "instance_id": "btc_macdx",
            "instance_ids": None,
            "reason": "panel",
        },
    )]


def test_disable_symbol_writes_stop_command(monkeypatch):
    disabled_symbols = []
    commands = []

    monkeypatch.setattr(trade_routes, "_read_disabled_symbols", lambda: list(disabled_symbols))
    monkeypatch.setattr(trade_routes, "_write_disabled_symbols", lambda items: disabled_symbols.extend(items) or True)
    monkeypatch.setattr(
        trade_routes,
        "write_symbol_command",
        lambda action, **kwargs: commands.append((action, kwargs)) or {"id": "cmd", "action": action},
    )

    result = asyncio.run(trade_routes.disable_symbol("BTC-USDT", {"user": {"id": 1}}))

    assert result["status"] == "success"
    assert result["symbol"] == "BTCUSDT"
    assert disabled_symbols == ["BTCUSDT"]
    assert commands[0][0] == "stop"
    assert commands[0][1]["symbol"] == "BTCUSDT"
