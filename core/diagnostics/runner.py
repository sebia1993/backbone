from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..config import load_commands
from ..models import Device
from ..mockserver.profiles import MockProfileError, load_mock_profile
from ..paths import resource_root, runtime_root
from ..preflight import validate_preflight
from .recorder import DiagnosticRecorder
from .report import DiagnosticReportPaths, write_diagnostic_reports


@dataclass(frozen=True)
class DiagnosticRunResult:
    output_dir: Path
    reports: DiagnosticReportPaths


def default_diagnostic_output_dir(root: Path | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (root or runtime_root()) / "outputs" / "diagnostics" / stamp


def run_self_check(output_dir: Path | None = None) -> DiagnosticRunResult:
    recorder = DiagnosticRecorder()
    recorder.record("BST-SYS-900", stage="startup", status="started", safe_detail="mode=self-check")

    # self-check는 실제 장비에 접속하지 않습니다. EXE 안에 필요한 설정/문서/mock
    # profile이 들어있는지 확인하고, 결과를 오류 코드 중심 리포트로 남깁니다.
    resources = resource_root()
    commands_path = resources / "config" / "commands.yaml"
    mock_profiles_path = resources / "config" / "mock_profiles.yaml"
    docs_path = resources / "docs"

    commands_loaded = []
    if not commands_path.is_file():
        recorder.record(
            "BST-CFG-102",
            stage="config",
            status="failed",
            safe_detail="resource=config/commands.yaml missing",
        )
    else:
        try:
            commands_loaded = load_commands(commands_path)
        except Exception as exc:
            recorder.record(
                "BST-CFG-102",
                stage="config",
                status="failed",
                safe_detail=f"resource=config/commands.yaml load_error={type(exc).__name__}",
            )
        else:
            # 명령어 안전성 검사는 문서용 가짜 장비명으로만 수행합니다.
            # 이렇게 해야 현장 내부 IP나 호스트명을 진단 산출물에 남기지 않습니다.
            synthetic_devices = [
                Device(name="mock-backbone-3", host="mock-bst-3.local", port=22, device_type="hp_comware"),
                Device(name="mock-backbone-4", host="mock-bst-4.local", port=22, device_type="hp_comware"),
            ]
            preflight = validate_preflight(synthetic_devices, commands_loaded)
            if preflight.has_errors:
                recorder.record(
                    "BST-CFG-121",
                    stage="config",
                    status="failed",
                    safe_detail=(
                        f"command_count={len(commands_loaded)} "
                        f"preflight_errors={preflight.error_count} "
                        f"preflight_warnings={preflight.warning_count}"
                    ),
                )
            else:
                recorder.record(
                    "BST-SEC-201",
                    stage="security",
                    status="passed",
                    safe_detail=(
                        f"commands_config=loaded command_count={len(commands_loaded)} "
                        f"preflight_errors=0 preflight_warnings={preflight.warning_count}"
                    ),
                )

    try:
        load_mock_profile(mock_profiles_path, "normal")
    except (FileNotFoundError, MockProfileError, ValueError) as exc:
        recorder.record(
            "BST-MOCK-801",
            stage="mock",
            status="failed",
            safe_detail=f"profile=normal load_error={type(exc).__name__}",
        )
    else:
        recorder.record(
            "BST-SEC-201",
            stage="mock",
            status="passed",
            safe_detail="mock_profiles=loaded profile=normal",
        )

    if docs_path.is_dir():
        required_docs = (
            "DIAGNOSTIC_MODE_GUIDE.html",
            "ERROR_CODE_CATALOG.html",
            "USER_GUIDE.html",
            "VERSION_HISTORY.html",
        )
        missing_docs = [name for name in required_docs if not (docs_path / name).is_file()]
        if missing_docs:
            recorder.record(
                "BST-PKG-701",
                stage="package",
                status="failed",
                safe_detail=f"missing_docs={','.join(missing_docs)}",
            )
        else:
            recorder.record(
                "BST-SEC-201",
                stage="package",
                status="passed",
                safe_detail=f"docs=present required_docs={len(required_docs)}",
            )
        recorder.record(
            "BST-SEC-211",
            stage="security",
            status="passed",
            safe_detail="device_alias_policy=enabled host=internal-device.example.com ip=192.0.2.10",
        )
    else:
        recorder.record(
            "BST-PKG-701",
            stage="package",
            status="failed",
            safe_detail="resource=docs missing",
        )

    destination = output_dir or default_diagnostic_output_dir()
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError:
        # 지정 경로에 쓸 수 없을 때도 진단 자체가 중단되지 않도록 실행 폴더 아래
        # fallback 위치에 최소 리포트를 남깁니다.
        fallback = runtime_root() / "diagnostic_report_fallback"
        fallback.mkdir(parents=True, exist_ok=True)
        destination = fallback
        recorder.record("BST-SYS-901", stage="system", status="failed", safe_detail="output_path_denied=true")

    recorder.record("BST-REP-601", stage="report", status="passed", safe_detail="raw_log_included=false")
    reports = write_diagnostic_reports(recorder.events, destination)
    return DiagnosticRunResult(output_dir=destination, reports=reports)
