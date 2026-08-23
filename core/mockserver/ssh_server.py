from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable
from typing import Any

from .profiles import MockProfile


class SshMockServer:
    def __init__(self, profile: MockProfile, host: str = "127.0.0.1", port: int = 0) -> None:
        self.profile = profile
        self.host = host
        self.requested_port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._host_key: Any = None

    @property
    def port(self) -> int:
        if self._sock is None:
            return self.requested_port
        return int(self._sock.getsockname()[1])

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    @property
    def host_key(self) -> Any:
        if self._host_key is None:
            raise RuntimeError("모의 SSH 서버가 시작되지 않았습니다.")
        return self._host_key

    @property
    def known_hosts_name(self) -> str:
        if self.port == 22:
            return self.host
        return f"[{self.host}]:{self.port}"

    def start(self) -> "SshMockServer":
        paramiko = _paramiko()
        self._host_key = paramiko.ECDSAKey.generate(bits=256)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.requested_port))
        self._sock.listen(100)
        self._sock.settimeout(0.5)
        self._thread = threading.Thread(target=self._accept_loop, name="bst-ssh-mock", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def __enter__(self) -> "SshMockServer":
        return self.start()

    def __exit__(self, *_args: Any) -> None:
        self.stop()

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self._sock is None:
                    return
                client, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()

    def _handle_client(self, client: socket.socket) -> None:
        paramiko = _paramiko()
        transport = paramiko.Transport(client)
        try:
            transport.add_server_key(self._host_key)
            server = _ParamikoServer(self.profile)
            transport.start_server(server=server)
            channel = transport.accept(10)
            if channel is None:
                return
            deadline = time.time() + 10
            while time.time() < deadline and not (server.exec_event.is_set() or server.shell_event.is_set()):
                time.sleep(0.02)
            if server.exec_event.is_set():
                response = self.profile.response_for(server.exec_command)
                _safe_send(channel, _ensure_newline(response).encode("utf-8", errors="replace"))
                _safe_send_exit_status(channel, 0)
                _safe_close(channel)
                return
            if server.shell_event.is_set():
                _serve_shell(channel, self.profile)
        except (EOFError, OSError, paramiko.SSHException):
            return
        finally:
            transport.close()


class _ParamikoServer:
    def __init__(self, profile: MockProfile) -> None:
        paramiko = _paramiko()
        self._base = paramiko.ServerInterface
        self.profile = profile
        self.exec_command = ""
        self.exec_event = threading.Event()
        self.shell_event = threading.Event()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base(), name)

    def check_auth_password(self, username: str, password: str) -> int:
        paramiko = _paramiko()
        if self.profile.accepts_login(username, password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "password"

    def check_channel_request(self, kind: str, chanid: int) -> int:
        paramiko = _paramiko()
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel: Any, term: str, width: int, height: int, pixelwidth: int, pixelheight: int, modes: bytes) -> bool:
        return True

    def check_channel_shell_request(self, channel: Any) -> bool:
        self.shell_event.set()
        return True

    def check_channel_exec_request(self, channel: Any, command: bytes) -> bool:
        self.exec_command = command.decode("utf-8", errors="replace").strip()
        self.exec_event.set()
        return True


def _serve_shell(channel: Any, profile: MockProfile) -> None:
    if not _safe_send(channel, (profile.banner + "\r\n" + profile.prompt).encode("utf-8", errors="replace")):
        return
    buffer = ""
    while True:
        try:
            data = channel.recv(4096)
        except OSError:
            return
        if not data:
            return
        buffer += data.decode("utf-8", errors="replace")
        while "\n" in buffer or "\r" in buffer:
            separators = [index for index in (buffer.find("\n"), buffer.find("\r")) if index >= 0]
            index = min(separators)
            line = buffer[:index].strip()
            buffer = buffer[index + 1 :]
            if not line:
                if not _safe_send(channel, profile.prompt.encode("utf-8", errors="replace")):
                    return
                continue
            if line.lower() in {"quit", "exit", "logout"}:
                _safe_send(channel, b"Connection closed.\r\n")
                _safe_close(channel)
                return
            delay = profile.delay_for(line)
            if delay > 0:
                time.sleep(delay)
            if not _safe_send(channel, (_ensure_newline(profile.response_for(line)) + profile.prompt).encode("utf-8", errors="replace")):
                return


def _ensure_newline(value: str) -> str:
    return value.rstrip("\r\n") + "\r\n"


def _safe_send(channel: Any, payload: bytes) -> bool:
    try:
        channel.send(payload)
    except (EOFError, OSError):
        return False
    return True


def _safe_send_exit_status(channel: Any, status: int) -> None:
    try:
        channel.send_exit_status(status)
    except (EOFError, OSError):
        pass


def _safe_close(channel: Any) -> None:
    try:
        channel.close()
    except (EOFError, OSError):
        pass


def _paramiko() -> Any:
    try:
        import paramiko
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("모의 SSH 서버에는 paramiko가 필요합니다.") from exc
    return paramiko


def run_ssh_server_forever(profile: MockProfile, host: str, port: int, log: Callable[[str], None] = print) -> None:
    server = SshMockServer(profile, host=host, port=port).start()
    try:
        log(f"모의 SSH 서버 대기 중: {server.host}:{server.port} 프로파일={profile.name}")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("모의 SSH 서버를 중지합니다.")
    finally:
        server.stop()
