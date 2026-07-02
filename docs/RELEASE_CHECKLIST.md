# 백본 상태 추적기 릴리스 반입 체크리스트

문서 버전: v0.8.57
작성일: 2026-06-15
대상: 사외 개발 ZIP을 사내 환경으로 반입해 검증하는 운영자와 인수자

## 1. 수령 파일

```text
backbone_state_tracker_v0.8.57_YYYYMMDD_source.zip
backbone_state_tracker_v0.8.57_YYYYMMDD_source.zip.sha256.txt
backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip
backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip.sha256.txt
backbone_state_tracker_v0.8.57_YYYYMMDD_release_manifest.txt
backbone_state_tracker_v0.8.57_YYYYMMDD_verify_release_package.ps1
```

## 2. ZIP 내부 필수 확인

- `PACKAGE_INFO.txt`
- `README.md`
- `RELEASE_NOTES.md`
- `CHANGELOG.md`
- `config/commands.yaml`
- `config/devices.example.yaml`
- `docs/USER_GUIDE.md`와 `docs/USER_GUIDE.html`
- `docs/COMMAND_GUIDE.md`와 `docs/COMMAND_GUIDE.html`
- `docs/DEVELOPER_GUIDE_BEGINNER.md`와 `docs/DEVELOPER_GUIDE_BEGINNER.html`
- `docs/VERSION_HISTORY.md`와 `docs/VERSION_HISTORY.html`
- `docs/RELEASE_CHECKLIST.md`와 `docs/RELEASE_CHECKLIST.html`
- `docs/images/settings-collection.png`
- `docs/images/compare-results.png`
- `docs/images/work-log.png`
- Source ZIP인 경우 `tests/*.py` 회귀 테스트 전체
- Source ZIP인 경우 `core/*.py` 런타임 모듈 전체와 `requirements.txt`
- Source ZIP인 경우 `tools/*.py`와 `tools/*.ps1` 릴리스 빌드/검증 스크립트 전체
- Windows EXE ZIP인 경우 `BackboneStateTracker.exe`, `RUN_FIRST.txt`

## 3. 포함되면 안 되는 항목

- `.git/`
- `outputs/`
- `raw/`
- `dist/`
- `build/`
- `.venv/`
- `venv/`
- `.pytest_cache/`
- `config/devices.yaml`
- `__pycache__/`
- `.pyc`
- `.spec`

## 4. 해시와 manifest 검증

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip --require-manifest
powershell -ExecutionPolicy Bypass -File .\backbone_state_tracker_v0.8.57_YYYYMMDD_verify_release_package.ps1 -Package .\backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip -RequireManifest
```

검증기는 다음을 확인합니다.

- ZIP 파일명과 sidecar, manifest의 버전/날짜 일치
- ZIP 크기와 SHA256 일치
- ZIP 내부 경로가 `backbone_state_tracker/` 루트 아래에 있는지
- 필수 파일 포함 여부
- 현재 공유 가능한 `config/*` 파일 포함 여부. 단, 로컬 대상 장비 정보인 `config/devices.yaml`은 제외
- 현재 `docs/*.md`, `docs/*.html`, `docs/images/*` 파일 포함 여부
- Source ZIP의 전체 회귀 테스트 파일 포함 여부
- Source ZIP의 전체 런타임 core 모듈과 dependency 파일 포함 여부
- Source ZIP의 릴리스 빌드/검증 도구 스크립트 포함 여부
- Windows EXE ZIP의 `BackboneStateTracker.exe`와 `RUN_FIRST.txt` 포함 여부
- `outputs/`, `raw/`, `dist/`, `build/`, `.venv/`, `venv/`, `.pytest_cache/` 같은 로컬 산출물/환경 폴더 포함 여부
- 금지 경로 포함 여부
- ZIP 내부 중복 엔트리 여부
- manifest 중복 Package 레코드 여부

## 5. 실행 확인

- EXE ZIP을 별도 폴더에 해제합니다.
- `RUN_FIRST.txt`를 확인합니다.
- `BackboneStateTracker.exe`를 실행합니다.
- 첫 화면이 `장비 설정`인지 확인합니다.
- 좌측 메뉴가 `장비 설정`, `비교 결과`, `작업 로그` 순서인지 확인합니다.
- `샘플 검증 생성`으로 실제 장비 접속 없이 리포트 생성이 되는지 확인합니다.

## 6. UI 마감 확인

- 좌측 내비게이션이 어두운 운영 콘솔 레일이고 현재 메뉴가 teal 계열 배경으로 강조되는지 확인합니다.
- `장비 설정` 화면에서 접속 계정, 대상 장비, 상태 수집 흐름이 위에서 아래로 자연스럽게 이어지는지 확인합니다.
- `비교 결과` 화면에서 `긴급`, `주의`, `정보`, `변경없음` 등급 카드가 상태별 색상과 선택 배경으로 구분되는지 확인합니다.
- 변경 상세 행을 선택했을 때 `선택 변경 맥락` 패널이 등급, 장비, 명령, 유형, 라인을 표시하는지 확인합니다.
- `작업 로그` 화면이 어두운 고정폭 로그 표면으로 표시되고 시간/오류/리포트 경로를 읽기 쉬운지 확인합니다.
- 사용자 가이드의 `docs/images/settings-collection.png`, `docs/images/compare-results.png`, `docs/images/work-log.png`가 현재 v0.8.57 화면과 일치하는지 확인합니다.

## 7. README / Release 문서 최신화 확인

- `README.md`의 설치, 실행, 테스트, 빌드, 사용 방법이 현재 파일과 맞는지 확인합니다.
- `RELEASE_NOTES.md`의 자동 Release notes 형식과 GitHub Release asset 설명이 현재 workflow와 맞는지 확인합니다.
- `CHANGELOG.md`에 사용자에게 보이는 변경사항이 빠지지 않았는지 확인합니다.
- Git에 커밋할 파일과 GitHub Release에 업로드할 ZIP/SHA256 asset이 구분되어 있는지 확인합니다.
- 내부 IP, 실제 장비명, 계정, 비밀번호, 실제 로그, 고객 정보가 문서에 없는지 확인합니다.
- Windows EXE ZIP은 GitHub Actions Windows runner 또는 Windows PC에서 검증해야 하며, macOS에서 직접 Windows EXE를 만든다고 설명하지 않습니다.

## 8. 메일 업로드 차단 시

일부 메일 시스템은 `.exe`, `.py`, `.ps1`을 포함한 ZIP을 차단할 수 있습니다. 이 경우 ZIP을 메일에 첨부하지 말고 승인된 사내 파일 반입 절차를 사용합니다.
