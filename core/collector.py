from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from .connectivity import make_connectivity_result, sanitize_connection_error
from .models import CommandResult, CommandSpec, Device


ProgressCallback = Callable[[str], None]
COMMAND_TIMEOUT_CODE = "BST-COL-401"
PARTIAL_COLLECTION_CODE = "BST-COL-411"
COMMAND_TIMEOUT_HINTS = ("timeout", "timed out", "read_timeout", "netmikotimeout")


class CollectionError(RuntimeError):
    pass


def command_failure_code(exc: Exception) -> str:
    error_text = f"{type(exc).__name__} {exc}".lower()
    if any(hint in error_text for hint in COMMAND_TIMEOUT_HINTS):
        return COMMAND_TIMEOUT_CODE
    return PARTIAL_COLLECTION_CODE


def format_command_failure_message(exc: Exception) -> str:
    code = command_failure_code(exc)
    safe_error = sanitize_connection_error(str(exc))
    if code == COMMAND_TIMEOUT_CODE:
        reason = "명령 응답 시간이 초과됐습니다."
    else:
        reason = "일부 명령 수집에 실패했습니다."
    return f"{code} {reason} detail={safe_error}"


class SnapshotCollector:
    def __init__(self, timeout: int = 30, progress: Optional[ProgressCallback] = None) -> None:
        self.timeout = timeout
        self.progress = progress or (lambda message: None)

    def collect(
        self,
        devices: list[Device],
        commands: list[CommandSpec],
        username: str,
        password: str,
    ) -> dict[str, list[CommandResult]]:
        try:
            from netmiko import ConnectHandler
            from netmiko.exceptions import NetMikoAuthenticationException, NetMikoTimeoutException
        except ImportError as exc:  # pragma: no cover
            raise CollectionError("netmiko is required. Install it with: python -m pip install netmiko") from exc

        all_results: dict[str, list[CommandResult]] = {}
        for device in [item for item in devices if item.enabled]:
            self.progress(f"[{device.name}] connecting to {device.host}:{device.port}")
            connection = None
            device_results: list[CommandResult] = []
            all_results[device.name] = device_results
            try:
                connection = ConnectHandler(
                    device_type=device.device_type,
                    host=device.host,
                    port=device.port,
                    username=username,
                    password=password,
                    timeout=self.timeout,
                    conn_timeout=self.timeout,
                    auth_timeout=self.timeout,
                    banner_timeout=self.timeout,
                    fast_cli=False,
                )
                device_results.append(make_connectivity_result(device, True))
                failed_command_count = 0
                for command in commands:
                    result = CommandResult.started(device, command)
                    self.progress(f"[{device.name}] run: {command.command}")
                    try:
                        result.output = connection.send_command_timing(
                            command_string=command.command,
                            strip_prompt=False,
                            strip_command=False,
                            cmd_verify=False,
                            read_timeout=command.timeout or self.timeout,
                        )
                        result.success = True
                    except Exception as exc:
                        failed_command_count += 1
                        result.success = False
                        result.error_message = format_command_failure_message(exc)
                        if not command.allow_failure:
                            self.progress(
                                f"[{device.name}] required command failed: {command.id} ({command_failure_code(exc)})"
                            )
                    finally:
                        device_results.append(result.finish())
                if failed_command_count:
                    self.progress(
                        f"[{device.name}] partial collection: failed_commands={failed_command_count} ({PARTIAL_COLLECTION_CODE})"
                    )
            except NetMikoAuthenticationException as exc:
                device_results.append(make_connectivity_result(device, False, "authentication", str(exc)))
                self.progress(f"[{device.name}] authentication failed")
            except NetMikoTimeoutException as exc:
                device_results.append(make_connectivity_result(device, False, "timeout", str(exc)))
                self.progress(f"[{device.name}] connection timeout")
            except Exception as exc:
                device_results.append(make_connectivity_result(device, False, "connection", str(exc)))
                self.progress(f"[{device.name}] connection failed")
            finally:
                if connection is not None:
                    try:
                        connection.disconnect()
                    except Exception:
                        pass

        return all_results
