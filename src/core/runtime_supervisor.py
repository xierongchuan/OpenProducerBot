"""Supervisor для управления торговым runtime из кода бота."""

from __future__ import annotations

import json
import os
import signal
import time
from datetime import datetime, timezone
from multiprocessing import Process
from pathlib import Path
from typing import Any

from src.utils.logger import error, info, warning


DATA_DIR = Path(os.getenv("SERVO_DATA_DIR", "data"))
COMMAND_PATH = Path(os.getenv("SERVO_RUNTIME_COMMAND_PATH", str(DATA_DIR / "runtime_command.json")))
STATUS_PATH = Path(os.getenv("SERVO_RUNTIME_STATUS_PATH", str(DATA_DIR / "runtime_status.json")))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except FileNotFoundError:
        return None
    except Exception as exc:
        warning(f"⚠️ Не удалось прочитать runtime control файл {path}: {exc}")
        return None


def _run_trading_runtime() -> None:
    from src.main import main

    main()


class RuntimeSupervisor:
    """Держит процесс управления живым и запускает торговый runtime как дочерний процесс."""

    def __init__(
        self,
        command_path: Path = COMMAND_PATH,
        status_path: Path = STATUS_PATH,
        poll_interval: float | None = None,
        stop_timeout: float | None = None,
        start_on_boot: bool | None = None,
    ) -> None:
        self.command_path = command_path
        self.status_path = status_path
        self.poll_interval = poll_interval or float(os.getenv("SERVO_RUNTIME_CONTROL_INTERVAL", "1.0"))
        self.stop_timeout = stop_timeout or float(os.getenv("SERVO_RUNTIME_STOP_TIMEOUT", "25"))
        self.start_on_boot = (
            start_on_boot
            if start_on_boot is not None
            else os.getenv("SERVO_RUNTIME_START_ON_BOOT", "1") != "0"
        )
        self.runtime_process: Process | None = None
        self.state = "stopped"
        self.started_at: str | None = None
        self.stopped_at: str | None = None
        self.last_exit_code: int | None = None
        self.last_error: str | None = None
        self.last_command_id: str | None = None
        self.last_command_action: str | None = None
        self.last_command_at: str | None = None
        self._shutdown_requested = False

    def request_shutdown(self, signum: int | None = None) -> None:
        if self._shutdown_requested:
            return
        signal_name = signal.Signals(signum).name if signum else "manual"
        info(f"🛑 Supervisor получил сигнал остановки: {signal_name}")
        self._shutdown_requested = True

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, lambda signum, _frame: self.request_shutdown(signum))
        signal.signal(signal.SIGINT, lambda signum, _frame: self.request_shutdown(signum))

    def _runtime_pid(self) -> int | None:
        if self.runtime_process and self.runtime_process.is_alive():
            return self.runtime_process.pid
        return None

    def _write_status(self) -> None:
        payload = {
            "state": self.state,
            "control_enabled": True,
            "supervisor_pid": os.getpid(),
            "runtime_pid": self._runtime_pid(),
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "last_exit_code": self.last_exit_code,
            "last_error": self.last_error,
            "last_command_id": self.last_command_id,
            "last_command_action": self.last_command_action,
            "last_command_at": self.last_command_at,
            "updated_at": _utc_now(),
            "updated_at_ts": time.time(),
        }
        try:
            _atomic_write_json(self.status_path, payload)
        except Exception as exc:
            warning(f"⚠️ Не удалось записать runtime status: {exc}")

    def _refresh_state(self) -> None:
        if self.runtime_process is None:
            return
        if self.runtime_process.is_alive():
            if self.state not in {"starting", "running", "restarting"}:
                self.state = "running"
            return

        exit_code = self.runtime_process.exitcode
        self.runtime_process.join(timeout=0)
        self.runtime_process = None
        self.last_exit_code = exit_code
        self.stopped_at = _utc_now()
        if self.state in {"stopping", "stopped"}:
            self.state = "stopped"
        elif exit_code == 0:
            self.state = "stopped"
        else:
            self.state = "crashed"
            self.last_error = f"Runtime завершился с кодом {exit_code}"
            error(f"❌ {self.last_error}")

    def start_runtime(self, source: str = "manual") -> None:
        self._refresh_state()
        if self.runtime_process and self.runtime_process.is_alive():
            info(f"ℹ️ Runtime уже запущен (PID: {self.runtime_process.pid})")
            self.state = "running"
            return

        self.state = "starting"
        self.last_error = None
        self._write_status()

        process = Process(target=_run_trading_runtime, name="TradingRuntime")
        process.daemon = False
        process.start()

        self.runtime_process = process
        self.state = "running"
        self.started_at = _utc_now()
        self.stopped_at = None
        self.last_exit_code = None
        info(f"▶️ Runtime запущен через {source} (PID: {process.pid})")

    def stop_runtime(self, source: str = "manual") -> None:
        self._refresh_state()
        if not self.runtime_process or not self.runtime_process.is_alive():
            self.state = "stopped"
            self.stopped_at = self.stopped_at or _utc_now()
            info("ℹ️ Runtime уже остановлен")
            return

        process = self.runtime_process
        self.state = "stopping"
        self._write_status()
        info(f"⏹️ Останавливаю runtime через {source} (PID: {process.pid})")

        if process.pid:
            try:
                os.kill(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            except Exception as exc:
                warning(f"⚠️ Не удалось отправить SIGINT runtime: {exc}")

        process.join(timeout=self.stop_timeout)
        if process.is_alive():
            warning(f"⚠️ Runtime не остановился за {self.stop_timeout:.0f}s, отправляю terminate")
            process.terminate()
            process.join(timeout=5)
        if process.is_alive():
            warning("⚠️ Runtime всё ещё жив, отправляю kill")
            process.kill()
            process.join(timeout=3)

        self.last_exit_code = process.exitcode
        self.runtime_process = None
        self.state = "stopped"
        self.stopped_at = _utc_now()
        info(f"✅ Runtime остановлен через {source} (exit={self.last_exit_code})")

    def restart_runtime(self, source: str = "manual") -> None:
        info(f"🔄 Перезапуск runtime через {source}")
        self.state = "restarting"
        self._write_status()
        self.stop_runtime(source=source)
        time.sleep(1)
        self.start_runtime(source=source)

    def _handle_command(self, command: dict[str, Any]) -> None:
        command_id = str(command.get("id") or "")
        if not command_id or command_id == self.last_command_id:
            return

        action = str(command.get("action") or "").lower()
        requested_by = str(command.get("requested_by") or "panel")
        self.last_command_id = command_id
        self.last_command_action = action
        self.last_command_at = command.get("requested_at") or _utc_now()

        if action == "start":
            self.start_runtime(source=requested_by)
        elif action == "stop":
            self.stop_runtime(source=requested_by)
        elif action == "restart":
            self.restart_runtime(source=requested_by)
        else:
            self.last_error = f"Неизвестная runtime команда: {action}"
            warning(f"⚠️ {self.last_error}")

    def _poll_command(self) -> None:
        command = _read_json(self.command_path)
        if command:
            self._handle_command(command)

    def run(self) -> None:
        self.install_signal_handlers()
        info("🧭 Runtime supervisor запущен")
        existing_command = _read_json(self.command_path)
        if existing_command and existing_command.get("id"):
            self.last_command_id = str(existing_command["id"])
        self._write_status()

        if self.start_on_boot:
            self.start_runtime(source="startup")

        while not self._shutdown_requested:
            self._refresh_state()
            self._poll_command()
            self._write_status()
            time.sleep(self.poll_interval)

        self.stop_runtime(source="supervisor_shutdown")
        self._write_status()
        info("✅ Runtime supervisor остановлен")


def main() -> None:
    RuntimeSupervisor().run()


if __name__ == "__main__":
    main()
