"""Файловый control channel для управления worker-процессами отдельных символов."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.runtime import normalize_symbol_key


DATA_DIR = Path(os.getenv("SERVO_DATA_DIR", "data"))
COMMAND_PATH = Path(os.getenv("SERVO_SYMBOL_RUNTIME_COMMAND_PATH", str(DATA_DIR / "symbol_runtime_command.json")))
STATUS_PATH = Path(os.getenv("SERVO_SYMBOL_RUNTIME_STATUS_PATH", str(DATA_DIR / "symbol_runtime_status.json")))
ALLOWED_ACTIONS = {"start", "stop", "restart"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except FileNotFoundError:
        return None
    except Exception:
        return None


def build_symbol_command(
    action: str,
    *,
    requested_by: str = "panel",
    symbol: str | None = None,
    instance_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    action = str(action or "").lower()
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Unknown symbol runtime action: {action}")
    if not symbol and not instance_id:
        raise ValueError("symbol or instance_id is required")

    command: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "action": action,
        "requested_by": requested_by,
        "requested_at": utc_now(),
        "requested_at_ts": time.time(),
    }
    if symbol:
        command["symbol"] = normalize_symbol_key(symbol)
    if instance_id:
        command["instance_id"] = str(instance_id).lower()
    if reason:
        command["reason"] = str(reason)
    return command


def write_symbol_command(
    action: str,
    *,
    requested_by: str = "panel",
    symbol: str | None = None,
    instance_id: str | None = None,
    reason: str | None = None,
    command_path: Path = COMMAND_PATH,
) -> dict[str, Any]:
    command = build_symbol_command(
        action,
        requested_by=requested_by,
        symbol=symbol,
        instance_id=instance_id,
        reason=reason,
    )
    atomic_write_json(command_path, command)
    return command

