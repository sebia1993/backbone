from __future__ import annotations

import re
from dataclasses import dataclass


CODE_PATTERN = re.compile(r"^BST-[A-Z]{3,4}-\d{3}$")
SEVERITY_LABELS = {
    "Critical": "긴급",
    "Warning": "주의",
    "Info": "정보",
}


@dataclass(frozen=True)
class DiagnosticCode:
    code: str
    name: str
    severity: str
    area: str
    summary: str
    action_hint: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "name": self.name,
            "severity": self.severity,
            "area": self.area,
            "summary": self.summary,
            "action_hint": self.action_hint,
        }

    def explain(self) -> str:
        severity = SEVERITY_LABELS.get(self.severity, self.severity)
        return (
            f"{self.code} {self.name}\n"
            f"심각도: {severity}\n"
            f"영역: {self.area}\n"
            f"의미: {self.summary}\n"
            f"조치: {self.action_hint}"
        )


_CODE_LIST = (
    DiagnosticCode(
        "BST-CFG-101",
        "DEVICE_CONFIG_MISSING",
        "Critical",
        "config",
        "사용 가능한 대상 장비가 설정되지 않았습니다.",
        "장비 설정 화면에서 대상 장비를 1대 이상 추가하세요.",
    ),
    DiagnosticCode(
        "BST-CFG-102",
        "COMMAND_CONFIG_MISSING",
        "Critical",
        "config",
        "명령 설정 파일이 없습니다.",
        "반입한 패키지에 config/commands.yaml이 포함됐는지 확인하세요.",
    ),
    DiagnosticCode(
        "BST-CFG-121",
        "UNSAFE_COMMAND_BLOCKED",
        "Critical",
        "config",
        "쓰기/변경 가능성이 있는 명령이 설정 점검에서 차단됐습니다.",
        "차단된 명령을 제거하고 show/display 계열 읽기 전용 명령만 유지하세요.",
    ),
    DiagnosticCode(
        "BST-SEC-201",
        "SECRET_REDACTED",
        "Info",
        "security",
        "진단 산출물 저장 전 민감정보가 마스킹됐습니다.",
        "정상 동작입니다. 생성된 안전 진단 리포트만 공유하세요.",
    ),
    DiagnosticCode(
        "BST-SEC-211",
        "DEVICE_ALIAS_APPLIED",
        "Info",
        "security",
        "장비, 호스트, 주소 값이 안전한 alias로 치환됐습니다.",
        "외부 문의에는 alias만 사용하고 실제 매핑은 내부에만 보관하세요.",
    ),
    DiagnosticCode(
        "BST-CON-301",
        "TCP_TIMEOUT",
        "Critical",
        "connection",
        "TCP 연결 시간이 초과됐습니다.",
        "현장에서 장비 전원, 관리망 도달성, 방화벽 정책, 포트 번호를 확인하세요.",
    ),
    DiagnosticCode(
        "BST-CON-302",
        "SSH_AUTH_FAILED",
        "Critical",
        "connection",
        "SSH 인증에 실패했습니다.",
        "계정, 암호, SSH 권한, 장비 로그인 정책을 확인하세요.",
    ),
    DiagnosticCode(
        "BST-CON-303",
        "TELNET_LOGIN_FAILED",
        "Critical",
        "connection",
        "Telnet 로그인에 실패했습니다.",
        "계정, 암호, Telnet 접근 정책, 선택한 접속 방식을 확인하세요.",
    ),
    DiagnosticCode(
        "BST-CON-304",
        "CONNECTION_REFUSED",
        "Critical",
        "connection",
        "원격 포트가 연결을 거부했습니다.",
        "SSH/Telnet 서비스 활성화 여부와 설정된 포트 번호를 확인하세요.",
    ),
    DiagnosticCode(
        "BST-COL-401",
        "COMMAND_TIMEOUT",
        "Warning",
        "collection",
        "명령이 설정된 제한시간 안에 응답하지 않았습니다.",
        "장비 부하, 명령 실행 시간, timeout 값이 충분한지 확인하세요.",
    ),
    DiagnosticCode(
        "BST-COL-411",
        "DEVICE_PARTIAL_COLLECTION",
        "Warning",
        "collection",
        "일부 명령만 수집됐습니다.",
        "실패한 명령 코드와 장비 상태를 확인한 뒤 다시 진단하세요.",
    ),
    DiagnosticCode(
        "BST-DIF-501",
        "BASELINE_NOT_FOUND",
        "Warning",
        "diff",
        "비교 기준 스냅샷이 없습니다.",
        "후속 단계 수집 전에 작업 전 기준 스냅샷을 먼저 생성하세요.",
    ),
    DiagnosticCode(
        "BST-REP-601",
        "SAFE_REPORT_CREATED",
        "Info",
        "report",
        "원본 명령 출력 없이 안전 진단 리포트가 생성됐습니다.",
        "외부 분석 요청 시 진단 티켓 또는 안전 리포트를 공유하세요.",
    ),
    DiagnosticCode(
        "BST-PKG-701",
        "EXE_RESOURCE_MISSING",
        "Critical",
        "package",
        "EXE 실행에 필요한 리소스가 없습니다.",
        "Windows EXE ZIP을 재빌드/재반입하고 패키지 manifest를 검증하세요.",
    ),
    DiagnosticCode(
        "BST-MOCK-801",
        "MOCK_PROFILE_NOT_FOUND",
        "Critical",
        "mock",
        "요청한 모의 장비 프로파일을 찾을 수 없습니다.",
        "프로파일 이름과 config/mock_profiles.yaml 포함 여부를 확인하세요.",
    ),
    DiagnosticCode(
        "BST-SYS-900",
        "DIAGNOSTIC_SELF_CHECK_STARTED",
        "Info",
        "system",
        "진단 자체 점검이 시작됐습니다.",
        "이어지는 진단 이벤트를 확인하세요.",
    ),
    DiagnosticCode(
        "BST-SYS-901",
        "OUTPUT_PATH_DENIED",
        "Critical",
        "system",
        "진단 출력 폴더에 쓸 수 없습니다.",
        "폴더 권한을 확인하거나 승인된 쓰기 가능 폴더에서 실행하세요.",
    ),
)

DIAGNOSTIC_CODES = {item.code: item for item in _CODE_LIST}


def list_codes() -> list[DiagnosticCode]:
    return list(_CODE_LIST)


def get_code(code: str) -> DiagnosticCode | None:
    return DIAGNOSTIC_CODES.get(str(code).strip().upper())


def explain_code(code: str) -> str:
    item = get_code(code)
    if item is None:
        return (
            f"{str(code).strip().upper()} UNKNOWN\n"
            "심각도: 알 수 없음\n"
            "영역: unknown\n"
            "의미: 이 애플리케이션 버전에 등록되지 않은 진단 코드입니다.\n"
            "조치: 애플리케이션 버전과 패키지에 포함된 오류 코드 카탈로그를 확인하세요."
        )
    return item.explain()


def validate_catalog() -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for item in _CODE_LIST:
        if item.code in seen:
            errors.append(f"Duplicate diagnostic code: {item.code}")
        seen.add(item.code)
        if not CODE_PATTERN.match(item.code):
            errors.append(f"Invalid diagnostic code format: {item.code}")
        if item.severity not in {"Critical", "Warning", "Info"}:
            errors.append(f"Invalid severity for {item.code}: {item.severity}")
        for field_name in ("name", "area", "summary", "action_hint"):
            if not getattr(item, field_name).strip():
                errors.append(f"Missing {field_name} for {item.code}")
    return errors
