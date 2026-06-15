from __future__ import annotations

import socketserver
import threading
import time
from collections.abc import Callable
from typing import Any

from .profiles import MockProfile


class _ThreadingTcpServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _line_bytes(value: str) -> bytes:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    return normalized.encode("utf-8", errors="replace")


class TelnetMockServer:
    def __init__(self, profile: MockProfile, host: str = "127.0.0.1", port: int = 0) -> None:
        self.profile = profile
        self.host = host
        self.requested_port = port
        self._server: _ThreadingTcpServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        if self._server is None:
            return self.requested_port
        return int(self._server.server_address[1])

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    def start(self) -> "TelnetMockServer":
        handler = self._make_handler()
        self._server = _ThreadingTcpServer((self.host, self.requested_port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="bst-telnet-mock", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def __enter__(self) -> "TelnetMockServer":
        return self.start()

    def __exit__(self, *_args: Any) -> None:
        self.stop()

    def _make_handler(self) -> type[socketserver.StreamRequestHandler]:
        profile = self.profile

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:
                self._send(f"{profile.banner}\r\nUsername: ")
                username = self._readline()
                self._send("Password: ")
                password = self._readline()
                if not profile.accepts_login(username, password):
                    self._send("Authentication failed.\r\n")
                    return
                self._send(profile.prompt)
                while True:
                    command = self._readline()
                    if not command:
                        return
                    normalized = " ".join(command.split())
                    if normalized.lower() in {"quit", "exit", "logout"}:
                        self._send("Connection closed.\r\n")
                        return
                    delay = profile.delay_for(normalized)
                    if delay > 0:
                        time.sleep(delay)
                    response = profile.response_for(normalized)
                    if response:
                        self._send(response.rstrip("\r\n") + "\r\n")
                    self._send(profile.prompt)

            def _readline(self) -> str:
                data = self.rfile.readline(4096)
                return data.decode("utf-8", errors="replace").strip()

            def _send(self, value: str) -> None:
                self.wfile.write(_line_bytes(value))
                self.wfile.flush()

        return Handler


def run_telnet_server_forever(profile: MockProfile, host: str, port: int, log: Callable[[str], None] = print) -> None:
    server = TelnetMockServer(profile, host=host, port=port).start()
    try:
        log(f"Mock Telnet server listening on {server.host}:{server.port} profile={profile.name}")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping mock Telnet server.")
    finally:
        server.stop()
