from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .snapshot import SnapshotStore, sanitize_filename


PRE_WORK_STAGE = "작업 전"
BB3_OFF_STAGE = "백본3 OFF 중"
POST_RESTORE_STAGE = "복구 후"
CUSTOM_STAGE = "사용자 지정"
DEFAULT_STAGE_LABEL_PREFIX = "점검시간"


@dataclass(frozen=True)
class WorkStage:
    name: str
    slug: str
    description: str
    auto_compare: bool


WORK_STAGES = [
    WorkStage(PRE_WORK_STAGE, "pre_work", "작업 전 기준 상태를 저장합니다.", False),
    WorkStage(BB3_OFF_STAGE, "bb3_off", "백본3 OFF 중 상태를 수집하고 작업 전과 자동 비교합니다.", True),
    WorkStage(POST_RESTORE_STAGE, "post_restore", "복구 후 상태를 수집하고 작업 전과 자동 비교합니다.", True),
    WorkStage(CUSTOM_STAGE, "custom", "사용자 지정 단계명을 저장하고 작업 전과 자동 비교합니다.", True),
]

WORK_STAGE_NAMES = [stage.name for stage in WORK_STAGES]
WORK_STAGE_BY_NAME = {stage.name: stage for stage in WORK_STAGES}


def default_stage_label(now: datetime | None = None) -> str:
    moment = now or datetime.now()
    return f"{DEFAULT_STAGE_LABEL_PREFIX}_{moment:%Y%m%d_%H%M}"


def resolve_stage(stage_name: str, custom_label: str = "", now: datetime | None = None) -> WorkStage:
    stage = WORK_STAGE_BY_NAME.get(stage_name, WORK_STAGE_BY_NAME[PRE_WORK_STAGE])
    display_name = custom_label.strip() or default_stage_label(now)
    if stage.name != CUSTOM_STAGE:
        return WorkStage(display_name, stage.slug, stage.description, stage.auto_compare)

    custom_name = display_name
    custom_slug = sanitize_filename(custom_name, "custom_snapshot")
    return WorkStage(custom_name, custom_slug, "사용자 지정 단계입니다.", True)


def build_snapshot_folder_label(stage: WorkStage) -> str:
    return stage.name


def find_latest_pre_work_snapshot(snapshot_dirs: list[Path]) -> Path | None:
    latest: Path | None = None
    for snapshot_dir in snapshot_dirs:
        try:
            snapshot = SnapshotStore.load_snapshot(snapshot_dir)
        except Exception:
            continue
        if is_sample_snapshot(snapshot_dir, snapshot.stage_slug):
            continue
        is_pre_work = (
            snapshot.stage_slug == WORK_STAGE_BY_NAME[PRE_WORK_STAGE].slug
            or snapshot.label == PRE_WORK_STAGE
            or snapshot_dir.name.endswith("_pre_work")
        )
        if not is_pre_work:
            continue
        if latest is None or snapshot_dir.name > latest.name:
            latest = snapshot_dir
    return latest


def is_sample_snapshot(snapshot_dir: Path, stage_slug: str = "") -> bool:
    return stage_slug.startswith("sample_") or "_sample_" in snapshot_dir.name


SEVERITY_LABELS_KO = {
    "Critical": "긴급",
    "Warning": "주의",
    "Info": "정보",
    "Unchanged": "변경없음",
}

STATUS_LABELS_KO = {
    "changed": "변경됨",
    "unchanged": "변경없음",
    "added": "추가됨",
    "removed": "삭제됨",
}


def severity_to_korean(value: str) -> str:
    return SEVERITY_LABELS_KO.get(value, value)


def status_to_korean(value: str) -> str:
    return STATUS_LABELS_KO.get(value, value)
