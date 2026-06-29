from __future__ import annotations

import argparse
import socket
from pathlib import Path

from .profiles import MockProfile, load_mock_profile
from .ssh_server import SshMockServer, run_ssh_server_forever
from .telnet_server import TelnetMockServer, run_telnet_server_forever
from ..paths import resource_root


def default_profile_path() -> Path:
    return resource_root() / "config" / "mock_profiles.yaml"


def run_mock_server_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="백본 상태 추적기 모의 SSH/Telnet 서버를 실행합니다.")
    parser.add_argument("--mock-server", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--protocol", choices=("telnet", "ssh"), default="telnet")
    parser.add_argument("--profile", default="normal")
    parser.add_argument("--profile-path", type=Path, default=default_profile_path())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    profile = load_mock_profile(args.profile_path, args.profile)
    if args.self_check:
        # self-check는 서버를 잠깐 띄운 뒤 직접 접속해 응답을 확인합니다.
        # 장기 실행 서버 모드와 달리 테스트가 끝나면 즉시 종료됩니다.
        if args.protocol == "ssh":
            return _self_check_ssh(profile, args.host, args.port)
        return _self_check_telnet(profile, args.host, args.port)

    # self-check가 없으면 개발자가 수동 테스트에 사용할 mock 장비처럼 계속 대기합니다.
    if args.protocol == "ssh":
        run_ssh_server_forever(profile, args.host, args.port)
    else:
        run_telnet_server_forever(profile, args.host, args.port)
    return 0


def _self_check_telnet(profile: MockProfile, host: str, port: int) -> int:
    with TelnetMockServer(profile, host=host, port=port) as server:
        with socket.create_connection(server.address, timeout=5) as sock:
            sock.settimeout(5)
            _recv_until(sock, b"Username: ")
            sock.sendall((profile.username + "\n").encode("utf-8"))
            _recv_until(sock, b"Password: ")
            sock.sendall((profile.password + "\n").encode("utf-8"))
            _recv_until(sock, profile.prompt.encode("utf-8"))
            sock.sendall(b"display clock\n")
            payload = _recv_until(sock, profile.prompt.encode("utf-8"))
            if b"Mock clock" not in payload:
                raise RuntimeError("모의 Telnet 자체 점검에서 예상한 명령 응답을 받지 못했습니다.")
        print(f"모의 telnet 자체 점검 OK host={server.host} port={server.port} profile={profile.name}")
    return 0


def _self_check_ssh(profile: MockProfile, host: str, port: int) -> int:
    try:
        import paramiko
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("모의 SSH 자체 점검에는 paramiko가 필요합니다.") from exc
    with SshMockServer(profile, host=host, port=port) as server:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                server.host,
                port=server.port,
                username=profile.username,
                password=profile.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=5,
                banner_timeout=5,
                auth_timeout=5,
            )
            _stdin, stdout, _stderr = client.exec_command("display clock", timeout=5)
            payload = stdout.read().decode("utf-8", errors="replace")
            if "Mock clock" not in payload:
                raise RuntimeError("모의 SSH 자체 점검에서 예상한 명령 응답을 받지 못했습니다.")
        finally:
            client.close()
        print(f"모의 ssh 자체 점검 OK host={server.host} port={server.port} profile={profile.name}")
    return 0


def _recv_until(sock: socket.socket, marker: bytes) -> bytes:
    # Telnet 응답은 한 번에 모두 오지 않을 수 있으므로 원하는 프롬프트가 보일 때까지
    # 조각을 모읍니다. mock 테스트에서 실제 네트워크 지연을 흉내 내기 위한 기본 패턴입니다.
    chunks: list[bytes] = []
    while marker not in b"".join(chunks):
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)
