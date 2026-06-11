# Backbone State Tracker 초급 개발자 가이드

문서 버전: v0.8.11
작성일: 2026-06-12
대상: Python과 Windows 배포를 처음 유지보수하는 개발자

## 1. 프로젝트 목적

이 도구는 백본 3/4호기의 작업 전후 상태를 수집하고, 특정 시점끼리 비교해 변경점을 추적하는 Windows GUI 프로그램입니다. 장비 설정 변경이 아니라 읽기 전용 점검과 리포트 생성을 목표로 합니다.

## 2. 주요 폴더와 파일

- `app.py`: 프로그램 시작점입니다.
- `core/gui.py`: Tkinter GUI 화면과 사용자 이벤트 처리입니다.
- `core/collector.py`: Netmiko 기반 SSH 명령 수집입니다.
- `core/connectivity.py`: 장비별 접속 상태 내부 결과를 생성합니다.
- `core/preflight.py`: 수집 전 장비/명령 설정 검증 규칙입니다.
- `core/mock_validation.py`: 실제 장비 없이 샘플 스냅샷과 비교 리포트를 생성합니다.
- `core/redaction.py`: 로그, 메타데이터, 리포트에 표시되는 명백한 비밀값을 마스킹합니다.
- `core/report_bundle.py`: 공유용 리포트 ZIP을 생성하고 raw 출력 제외 규칙을 관리합니다.
- `core/snapshot.py`: 스냅샷 저장과 로드입니다.
- `core/diff_engine.py`: 스냅샷 비교 엔진입니다.
- `core/reporter.py`: HTML, XLSX, JSON 리포트 생성입니다.
- `core/workflow.py`: 작업 단계와 자동 비교 기준입니다.
- `core/workflow_wizard.py`: 대시보드 작업 진행 마법사의 단계 상태 계산입니다.
- `core/version.py`: 프로그램 버전 정보입니다.
- `config/commands.yaml`: 장비에 실행할 읽기 전용 점검 명령입니다.
- `config/devices.example.yaml`: 장비 설정 예시입니다.
- `docs/COMMAND_GUIDE.md`, `docs/COMMAND_GUIDE.html`: 운영자용 명령어 의미와 확인 포인트입니다.
- `docs/RELEASE_CHECKLIST.md`, `docs/RELEASE_CHECKLIST.html`: 사내 반입 시 파일 세트, 해시, ZIP 내용, 실행 확인 순서입니다.
- `tests/`: 단위 테스트입니다.
- `tools/build_release.ps1`: 소스 ZIP 생성 스크립트입니다.
- `tools/build_windows_exe.ps1`: Windows EXE ZIP 생성 스크립트입니다.
- `tools/write_release_manifest.py`: 배포 ZIP의 SHA256 체크섬과 릴리스 매니페스트를 생성합니다.
- `tools/verify_release_package.py`: 배포 ZIP의 해시, 필수 파일, 금지 경로, ZIP 루트/경로 안전성을 검증합니다.
- `tools/verify_release_package.ps1`: 소스 폴더 없이 PowerShell만으로 배포 ZIP을 같은 기준으로 검증합니다.

## 3. 개발 환경 준비

```powershell
cd "<folder-that-contains-backbone_state_tracker>\backbone_state_tracker"
python -m pip install -r requirements.txt
```

소스에서 실행할 때는 프로젝트 상위 폴더가 `PYTHONPATH`에 들어가야 합니다.
`<folder-that-contains-backbone_state_tracker>`는 실제 압축 해제 위치 또는 내부 작업 폴더로 바꿔 실행합니다.

```powershell
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python app.py
```

## 4. 테스트와 Smoke Check

변경 후 최소한 아래 명령을 실행합니다.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
```

`--smoke-check`는 GUI를 실제로 생성했다가 닫으며, 주요 페이지가 만들어지는지 확인합니다.

v0.6.0부터 비교 결과는 `DiffItem.diff` 원본 unified diff와 함께 `changed_lines`, `change_count`, `change_preview`를 저장합니다. 리포트나 GUI를 수정할 때는 두 표현이 모두 유지되는지 확인합니다.
v0.7.1부터 HTML 리포트의 변경 상세는 `유형`, `라인`, `변경 내용` 3열 구조입니다. GUI와 XLSX는 기존 분리 필드를 유지하므로 HTML 가독성 수정이 다른 출력 형식을 깨지 않는지 테스트로 확인합니다.
v0.7.2부터 모든 수집은 장비별 `device_connectivity` 결과를 포함합니다. 이 항목은 `config/commands.yaml`에 넣는 사용자 점검 명령이 아니라, 접속 성공/실패를 비교군에 넣기 위한 내부 결과입니다. 장비가 접속 불가이면 비교 엔진은 일반 명령 누락 노이즈를 숨기고 `device_connectivity` 한 건을 Critical로 표시합니다.
v0.7.3부터 `SnapshotStore._unique_snapshot_dir()`가 같은 초에 동일 단계 스냅샷을 여러 번 저장해도 폴더를 덮어쓰지 않도록 `_001`, `_002` 순번 폴더를 할당합니다. 관련 회귀 테스트는 `tests/test_snapshot.py`의 `test_write_snapshot_allocates_unique_folder_when_name_exists`입니다.
v0.7.4부터 GUI 비교 상세는 `판단`, `라인`, `변경 내용`을 한 행에 표시하고 선택 상세에 핵심 판단, 변경값, 원본 파일, 등급별 운영 메모를 표시합니다. 관련 포맷 테스트는 `tests/test_gui_formatting.py`입니다.
v0.7.5부터 `core/mock_validation.py`가 실제 장비 접속 없이 `[샘플]` 스냅샷 3개와 비교 리포트를 생성합니다. 관련 테스트는 `tests/test_mock_validation.py`입니다.
v0.7.6부터 `core/redaction.py`가 GUI 로그, 스냅샷 메타데이터, HTML/XLSX/JSON 비교 리포트의 명백한 비밀값을 `***`로 마스킹합니다. per-command `raw/*.txt` 출력은 운영 증거 보존을 위해 그대로 유지합니다. 관련 테스트는 `tests/test_redaction.py`와 `tests/test_reporter.py`입니다.
v0.7.7부터 `core/report_bundle.py`가 비교 리포트마다 공유용 ZIP을 생성합니다. ZIP에는 마스킹된 리포트와 사용자 문서만 넣고, `raw/`, `config/devices.yaml`, 실행파일은 제외합니다. 관련 테스트는 `tests/test_reporter.py`의 공유 ZIP 검증입니다.
v0.7.8부터 GUI 비교 상세 목록에 등급 필터와 검색 입력이 있습니다. 필터 검색은 표시용 마스킹 값을 기준으로 동작해야 하며, 관련 테스트는 `tests/test_gui_formatting.py`입니다.
v0.7.9부터 `core/preflight.py`가 실제 장비 접속 전에 장비/명령 설정을 로컬에서 검증합니다. 오류는 수집을 차단하고, 주의는 운영자가 확인 후 진행할 수 있습니다. 관련 테스트는 `tests/test_preflight.py`입니다.
v0.8.0부터 `tools/write_release_manifest.py`가 소스 ZIP과 Windows EXE ZIP의 SHA256 체크섬 파일 및 버전 단위 릴리스 매니페스트를 생성합니다. 관련 테스트는 `tests/test_release_manifest.py`입니다.
v0.8.1부터 `tools/verify_release_package.py`가 배포 ZIP의 sidecar 해시, manifest 기록, 필수 파일, 금지 파일 포함 여부를 검증합니다. 관련 테스트는 `tests/test_release_package_verifier.py`입니다.
v0.8.2부터 `tools/verify_release_package.ps1`가 버전명 포함 PowerShell 검증 스크립트로 `dist/`에 함께 생성됩니다. 이 스크립트는 Python 환경 없이 반입된 ZIP, `.sha256.txt`, `release_manifest.txt`를 검증합니다.
v0.8.3부터 수집/비교/샘플 검증 중복 실행을 GUI 진입점에서 차단합니다. 관련 회귀 테스트는 `tests/test_gui_formatting.py`의 busy guard 테스트입니다.
v0.8.4부터 `docs/COMMAND_GUIDE.md`와 `docs/COMMAND_GUIDE.html`이 배포 필수 문서에 포함됩니다. 패키지 검증 기준도 두 파일을 확인합니다.
v0.8.5부터 GUI의 도움말 메뉴와 상태 수집 화면에서 `COMMAND_GUIDE.html`을 바로 열 수 있습니다. 명령어 문서 파일명을 변경할 때는 `core/gui.py`의 `open_doc()` 호출도 함께 확인합니다.
v0.8.6부터 비교 상세 선택 행에서 기준/비교 `raw/*.txt`를 바로 열고, 마스킹된 선택 상세를 클립보드로 복사할 수 있습니다. 원본 파일 경로는 `DiffSummary.base_snapshot`, `DiffSummary.target_snapshot`, `DiffItem.base_raw_file`, `DiffItem.target_raw_file` 조합으로 계산합니다.
v0.8.7부터 README와 가이드는 특정 개발 PC의 절대 경로 대신 `<folder-that-contains-backbone_state_tracker>` 형태의 휴대 가능한 예시를 사용합니다. 문서를 수정할 때는 로컬 작업 경로가 배포 ZIP에 들어가지 않도록 확인합니다.
v0.8.8부터 `docs/RELEASE_CHECKLIST.md/html`이 배포 필수 문서에 포함됩니다. Python/PowerShell 패키지 검증기는 이 문서가 빠진 ZIP을 실패 처리합니다.
v0.8.9부터 Python/PowerShell 패키지 검증기는 ZIP 파일명 버전과 sidecar `Version`, manifest `Version`, manifest `Date stamp`가 일치하는지 확인합니다.
v0.8.10부터 Python/PowerShell 패키지 검증기는 sidecar의 대상 ZIP 이름과 manifest의 해당 패키지 `Size`/`SHA256` 레코드가 실제 ZIP과 일치하는지 확인합니다.
v0.8.11부터 Python/PowerShell 패키지 검증기는 ZIP 내부 엔트리가 `backbone_state_tracker/` 루트 안에 있고 절대 경로, 드라이브 경로, 빈 경로 조각, `..` 이동 조각을 쓰지 않는지 확인합니다.

## 5. UI 유지보수 기준

현재 GUI는 밝은 운영 콘솔 구조입니다.

- 좌측 메뉴: 대시보드, 상태 수집, 비교 결과, 장비 설정, 작업 로그
- 상단 상태 바: 현재 상태, 기준 스냅샷, 비교 대상
- 대시보드: 긴급/주의/정보/변경없음 지표와 최근 스냅샷/리포트
- 작업 진행 마법사: 장비 설정 확인부터 최종 확인까지 다음 액션 안내
- 비교 결과: 최근 변경 상세 목록, 판단/라인/변경 내용, 선택한 변경 행의 운영 메모
- 비교 상세 액션: 선택 행의 기준 원본, 비교 원본, 마스킹된 상세 복사
- 도움말/상태 수집 화면: 사용자 가이드, 명령어 가이드, 버전 변경내역 문서 접근
- 색상 기준: 초록 계열 강조색, 흰색 표면, 회색 경계선, 위험/주의/정보 색상 분리

UI를 수정할 때는 `core/gui.py`의 수집/비교 메서드 계약을 깨지 않도록 합니다.
마법사 단계 판단은 `core/workflow_wizard.py`의 순수 함수에서 관리하고, GUI는 그 결과를 표시하는 역할로 유지합니다.

## 6. 버전 업데이트 절차

1. `core/version.py`의 `APP_VERSION`을 올립니다.
2. `CHANGELOG.md`에 새 버전 항목을 추가합니다.
3. `docs/VERSION_HISTORY.md`, `docs/VERSION_HISTORY.html`, `docs/RELEASE_CHECKLIST.md/html`을 업데이트합니다.
4. 사용자 가이드와 개발자 가이드가 새 기능을 설명하는지 확인합니다.
5. 테스트와 smoke-check를 실행합니다.
6. 소스 ZIP과 Windows EXE ZIP을 생성합니다.
7. `dist/`의 ZIP, `.sha256.txt`, `release_manifest.txt`, `CURRENT_RELEASE.txt`, `latest/`를 확인합니다.
8. `python .\tools\verify_release_package.py .\dist\<package>.zip --require-manifest`로 배포 ZIP을 검증합니다. 파일명, sidecar, manifest의 버전/날짜/패키지 레코드와 ZIP 내부 경로 안전성이 맞는지도 확인합니다.
9. `powershell -ExecutionPolicy Bypass -File .\dist\<version>_verify_release_package.ps1 -Package .\dist\<package>.zip -RequireManifest`로 독립 PowerShell 검증도 확인합니다.
10. Git 브랜치, 커밋, 태그를 남깁니다.

## 7. 배포 파일 생성

소스 ZIP:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

Windows EXE ZIP:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

결과물은 `dist/` 폴더에 생성됩니다.
각 ZIP에는 `PACKAGE_INFO.txt`가 포함되고, ZIP 밖에는 같은 이름의 `.sha256.txt` 파일과 버전 단위 `release_manifest.txt`가 함께 생성됩니다.
빌드 스크립트는 ZIP 생성 후 `tools/verify_release_package.py`를 자동 실행하므로 필수 파일 누락이나 `config/devices.yaml`, `outputs/`, `raw/` 같은 금지 경로가 포함되면 실패합니다. 또한 ZIP 내부 파일이 `backbone_state_tracker/` 루트 밖에 있거나 절대 경로, 드라이브 경로, `..` 이동 경로를 쓰면 실패합니다.
또한 `dist/`에는 버전명이 포함된 `*_verify_release_package.ps1` 스크립트가 생성되어, 소스 폴더 없이 ZIP과 sidecar 파일만 전달된 환경에서도 검증할 수 있습니다.
빌드 후 `dist/latest/`와 `dist/CURRENT_RELEASE.txt`는 현재 버전의 반입 대상 파일 목록으로 갱신됩니다.

## 8. 보안 원칙

- 암호, 토큰, 실제 장비 출력 원본을 Git이나 배포 ZIP에 넣지 않습니다.
- `config/devices.yaml`은 로컬 운영 파일이므로 소스 ZIP에서 제외됩니다.
- `outputs/`는 수집 결과가 들어가므로 배포 ZIP에서 제외됩니다.
- 리포트, GUI, 로그에 새 문자열 출력을 추가할 때는 `core.redaction.redact_sensitive_text()` 또는 `redact_payload()` 적용 여부를 확인합니다.
- 공유 ZIP 구성을 변경할 때는 raw 출력 폴더, 로컬 장비 설정, 실행파일이 포함되지 않는지 테스트로 확인합니다.
- GUI 검색/필터를 수정할 때는 검색 대상에 민감값 원문이 들어가지 않는지 확인합니다.
- 수집 전 검증 규칙을 완화할 때는 변경성 명령이 통과하지 않는지 테스트를 함께 보강합니다.
- 장비 변경 명령은 `config/commands.yaml`에 추가하지 않습니다.
- README와 docs에는 개인 개발 PC 경로나 사내 특정 경로를 직접 적지 않습니다.
