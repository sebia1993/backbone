from __future__ import annotations

import re
from dataclasses import dataclass


CODE_PATTERN = re.compile(r"^BST-[A-Z]{3,4}-\d{3}$")


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
        return (
            f"{self.code} {self.name}\n"
            f"Severity: {self.severity}\n"
            f"Area: {self.area}\n"
            f"Meaning: {self.summary}\n"
            f"Action: {self.action_hint}"
        )


_CODE_LIST = (
    DiagnosticCode(
        "BST-CFG-101",
        "DEVICE_CONFIG_MISSING",
        "Critical",
        "config",
        "No enabled target device is configured.",
        "Add at least one target device in the device settings screen.",
    ),
    DiagnosticCode(
        "BST-CFG-102",
        "COMMAND_CONFIG_MISSING",
        "Critical",
        "config",
        "The command configuration file is missing.",
        "Check whether config/commands.yaml is included in the imported package.",
    ),
    DiagnosticCode(
        "BST-CFG-121",
        "UNSAFE_COMMAND_BLOCKED",
        "Critical",
        "config",
        "A write-capable or unsafe command was blocked by preflight.",
        "Remove the blocked command and keep only read-only show/display commands.",
    ),
    DiagnosticCode(
        "BST-SEC-201",
        "SECRET_REDACTED",
        "Info",
        "security",
        "Sensitive text was redacted before being stored in a diagnostic artifact.",
        "This is expected. Share only the generated safe diagnostic report.",
    ),
    DiagnosticCode(
        "BST-SEC-211",
        "DEVICE_ALIAS_APPLIED",
        "Info",
        "security",
        "A device, host, or address value was replaced with a safe alias.",
        "Use the alias in external communication and keep the real mapping internal.",
    ),
    DiagnosticCode(
        "BST-CON-301",
        "TCP_TIMEOUT",
        "Critical",
        "connection",
        "TCP connection timed out.",
        "Check device power, management network reachability, firewall policy, and port number on site.",
    ),
    DiagnosticCode(
        "BST-CON-302",
        "SSH_AUTH_FAILED",
        "Critical",
        "connection",
        "SSH authentication failed.",
        "Check the account, password, SSH permission, and device login policy on site.",
    ),
    DiagnosticCode(
        "BST-CON-303",
        "TELNET_LOGIN_FAILED",
        "Critical",
        "connection",
        "Telnet login failed.",
        "Check the account, password, Telnet access policy, and selected connection method.",
    ),
    DiagnosticCode(
        "BST-CON-304",
        "CONNECTION_REFUSED",
        "Critical",
        "connection",
        "The remote port refused the connection.",
        "Check whether SSH/Telnet service is enabled and whether the configured port is correct.",
    ),
    DiagnosticCode(
        "BST-COL-401",
        "COMMAND_TIMEOUT",
        "Warning",
        "collection",
        "A command did not return before the configured timeout.",
        "Check device load, command runtime, and whether the timeout value is sufficient.",
    ),
    DiagnosticCode(
        "BST-COL-411",
        "DEVICE_PARTIAL_COLLECTION",
        "Warning",
        "collection",
        "Only part of the command set was collected for a device.",
        "Review the failed command code and rerun the diagnostic after checking the device state.",
    ),
    DiagnosticCode(
        "BST-DIF-501",
        "BASELINE_NOT_FOUND",
        "Warning",
        "diff",
        "A baseline snapshot was not found for comparison.",
        "Create a pre-work baseline snapshot before collecting later stages.",
    ),
    DiagnosticCode(
        "BST-REP-601",
        "SAFE_REPORT_CREATED",
        "Info",
        "report",
        "A safe diagnostic report was created without raw command output.",
        "Share the diagnostic ticket or report when asking for external analysis.",
    ),
    DiagnosticCode(
        "BST-PKG-701",
        "EXE_RESOURCE_MISSING",
        "Critical",
        "package",
        "A required executable resource is missing.",
        "Rebuild or re-import the Windows EXE ZIP and verify the package manifest.",
    ),
    DiagnosticCode(
        "BST-MOCK-801",
        "MOCK_PROFILE_NOT_FOUND",
        "Critical",
        "mock",
        "The requested mock profile was not found.",
        "Check the profile name and whether config/mock_profiles.yaml is included.",
    ),
    DiagnosticCode(
        "BST-SYS-900",
        "DIAGNOSTIC_SELF_CHECK_STARTED",
        "Info",
        "system",
        "Diagnostic self-check started.",
        "Continue reviewing the generated diagnostic events.",
    ),
    DiagnosticCode(
        "BST-SYS-901",
        "OUTPUT_PATH_DENIED",
        "Critical",
        "system",
        "The diagnostic output directory is not writable.",
        "Check folder permissions or run the tool from an approved writable directory.",
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
            "Severity: Unknown\n"
            "Area: unknown\n"
            "Meaning: The diagnostic code is not registered in this application version.\n"
            "Action: Check the application version and the error-code catalog bundled with the package."
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
