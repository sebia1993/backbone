from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .snapshot import SnapshotStore
from .workflow import BB3_OFF_STAGE, POST_RESTORE_STAGE, PRE_WORK_STAGE


SETTINGS_STEP = "settings"
PRE_WORK_STEP = "pre_work"
BB3_OFF_STEP = "bb3_off"
OFF_REVIEW_STEP = "off_review"
POST_RESTORE_STEP = "post_restore"
FINAL_REVIEW_STEP = "final_review"
COMPLETE_STEP = "complete"


@dataclass(frozen=True)
class WizardStep:
    key: str
    title: str
    description: str
    status: str
    enabled: bool
    detail: str = ""


@dataclass(frozen=True)
class WorkflowWizardState:
    active_step: str
    next_action: str
    next_label: str
    next_enabled: bool
    message: str
    steps: list[WizardStep]
    pre_snapshot: Path | None = None
    off_snapshot: Path | None = None
    restore_snapshot: Path | None = None


def build_workflow_wizard_state(
    snapshot_dirs: list[Path],
    device_ready: bool,
    busy: bool = False,
    off_review_confirmed: bool = False,
    final_review_confirmed: bool = False,
    latest_counts: dict[str, int] | None = None,
) -> WorkflowWizardState:
    pre_snapshot = find_latest_stage_snapshot(snapshot_dirs, "pre_work")
    off_snapshot = find_latest_stage_snapshot(snapshot_dirs, "bb3_off")
    restore_snapshot = find_latest_stage_snapshot(snapshot_dirs, "post_restore")
    counts = latest_counts or {}

    if not device_ready:
        active_step = SETTINGS_STEP
        next_action = "open_settings"
        next_label = "장비 설정 확인"
        message = "백본 3/4호기 장비 정보와 접속 계정을 먼저 확인하세요."
    elif pre_snapshot is None:
        active_step = PRE_WORK_STEP
        next_action = "collect_pre"
        next_label = "작업 전 수집 시작"
        message = "작업 전 기준 스냅샷을 먼저 수집해야 이후 단계 자동 비교가 가능합니다."
    elif off_snapshot is None:
        active_step = BB3_OFF_STEP
        next_action = "collect_off"
        next_label = "백본3 OFF 중 수집 시작"
        message = "작업 전 기준이 준비되었습니다. 백본3 OFF 중 상태를 수집하세요."
    elif not off_review_confirmed:
        active_step = OFF_REVIEW_STEP
        next_action = "review_off"
        next_label = "OFF 중 변경 상세 확인"
        message = _review_message("백본3 OFF 중 자동 비교 결과를 확인하세요.", counts)
    elif restore_snapshot is None:
        active_step = POST_RESTORE_STEP
        next_action = "collect_restore"
        next_label = "복구 후 수집 시작"
        message = "OFF 중 변경 확인이 끝났습니다. 복구 후 상태를 수집하세요."
    elif not final_review_confirmed:
        active_step = FINAL_REVIEW_STEP
        next_action = "review_final"
        next_label = "최종 변경 상세 확인"
        message = _review_message("복구 후 자동 비교 결과를 확인하세요.", counts)
    else:
        active_step = COMPLETE_STEP
        next_action = "open_report"
        next_label = "최종 리포트 열기"
        message = "작업 흐름이 완료되었습니다. 최종 리포트와 로그를 보관하세요."

    if busy:
        next_action = "busy"
        next_label = "진행 중"
        message = "현재 수집 또는 비교가 진행 중입니다. 완료 후 다음 단계를 선택하세요."

    steps = [
        WizardStep(
            SETTINGS_STEP,
            "장비 설정 확인",
            "대상 장비와 접속 정보를 확인",
            _status_for(SETTINGS_STEP, active_step, complete=device_ready),
            enabled=not busy,
            detail="완료" if device_ready else "확인 필요",
        ),
        WizardStep(
            PRE_WORK_STEP,
            "작업 전 수집",
            "자동 비교 기준 스냅샷 생성",
            _status_for(PRE_WORK_STEP, active_step, complete=pre_snapshot is not None, locked=not device_ready),
            enabled=device_ready and not busy,
            detail=pre_snapshot.name if pre_snapshot else "대기",
        ),
        WizardStep(
            BB3_OFF_STEP,
            "백본3 OFF 중 수집",
            "작업 중 상태 수집 및 자동 비교",
            _status_for(BB3_OFF_STEP, active_step, complete=off_snapshot is not None, locked=pre_snapshot is None),
            enabled=pre_snapshot is not None and not busy,
            detail=off_snapshot.name if off_snapshot else "작업 전 필요",
        ),
        WizardStep(
            OFF_REVIEW_STEP,
            "OFF 중 변경 확인",
            "긴급/주의 변경 상세 검토",
            _status_for(OFF_REVIEW_STEP, active_step, complete=off_review_confirmed, locked=off_snapshot is None),
            enabled=off_snapshot is not None and not busy,
            detail=_counts_detail(counts) if off_snapshot else "수집 필요",
        ),
        WizardStep(
            POST_RESTORE_STEP,
            "복구 후 수집",
            "복구 상태 수집 및 자동 비교",
            _status_for(
                POST_RESTORE_STEP,
                active_step,
                complete=restore_snapshot is not None,
                locked=off_snapshot is None or not off_review_confirmed,
            ),
            enabled=off_snapshot is not None and off_review_confirmed and not busy,
            detail=restore_snapshot.name if restore_snapshot else "OFF 확인 필요",
        ),
        WizardStep(
            FINAL_REVIEW_STEP,
            "최종 확인",
            "최종 변경 상세와 리포트 확인",
            _status_for(FINAL_REVIEW_STEP, active_step, complete=final_review_confirmed, locked=restore_snapshot is None),
            enabled=restore_snapshot is not None and not busy,
            detail=_counts_detail(counts) if restore_snapshot else "복구 후 수집 필요",
        ),
    ]

    return WorkflowWizardState(
        active_step=active_step,
        next_action=next_action,
        next_label=next_label,
        next_enabled=not busy,
        message=message,
        steps=steps,
        pre_snapshot=pre_snapshot,
        off_snapshot=off_snapshot,
        restore_snapshot=restore_snapshot,
    )


def find_latest_stage_snapshot(snapshot_dirs: list[Path], stage_slug: str) -> Path | None:
    latest: Path | None = None
    stage_name = {
        "pre_work": PRE_WORK_STAGE,
        "bb3_off": BB3_OFF_STAGE,
        "post_restore": POST_RESTORE_STAGE,
    }.get(stage_slug, "")
    for snapshot_dir in snapshot_dirs:
        try:
            snapshot = SnapshotStore.load_snapshot(snapshot_dir)
        except Exception:
            continue
        is_stage = (
            snapshot.stage_slug == stage_slug
            or snapshot.stage_name == stage_name
            or snapshot.label == stage_name
            or snapshot_dir.name.endswith(f"_{stage_slug}")
        )
        if not is_stage:
            continue
        if latest is None or snapshot_dir.name > latest.name:
            latest = snapshot_dir
    return latest


def action_stage_name(action: str) -> str | None:
    return {
        "collect_pre": PRE_WORK_STAGE,
        "collect_off": BB3_OFF_STAGE,
        "collect_restore": POST_RESTORE_STAGE,
    }.get(action)


def _status_for(step: str, active_step: str, complete: bool, locked: bool = False) -> str:
    if complete:
        return "complete"
    if locked:
        return "locked"
    if step == active_step:
        return "current"
    return "pending"


def _counts_detail(counts: dict[str, int]) -> str:
    if not counts:
        return "비교 결과 대기"
    return (
        f"긴급 {counts.get('Critical', 0)}, "
        f"주의 {counts.get('Warning', 0)}, "
        f"정보 {counts.get('Info', 0)}, "
        f"변경없음 {counts.get('Unchanged', 0)}"
    )


def _review_message(prefix: str, counts: dict[str, int]) -> str:
    if counts.get("Critical", 0) or counts.get("Warning", 0):
        return f"{prefix} 긴급/주의 변경이 있으므로 상세 확인 후 다음 단계로 이동하세요."
    return prefix
