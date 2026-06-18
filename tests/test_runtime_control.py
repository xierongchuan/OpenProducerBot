import asyncio
import json
import time

import pytest
from fastapi import HTTPException

from src.core.runtime_supervisor import RuntimeSupervisor
from src.telegram_panel.backend.routes import runtime as runtime_routes


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
