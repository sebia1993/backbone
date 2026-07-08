# 백본 상태 추적기

버전: `v0.8.57`

HPE Aruba 계열 백본 3/4호기 상태를 읽기 전용 명령으로 수집하고, 작업 전후 스냅샷을 비교해 장애 징후와 변경점을 추적하는 Windows GUI/웹앱 도구입니다.

집에서 개발한 뒤 회사 내부망 PC에 반입해 실행하는 상황을 전제로 합니다. 실제 장비 로그, 내부 IP, 호스트명, 계정 정보는 외부로 반출하지 않고, 필요한 경우 모의 서버와 안전 진단 리포트로 검증합니다.

## 주요 기능

- 백본 장비에 SSH로 접속해 `config/commands.yaml`의 읽기 전용 점검 명령만 실행합니다.
- `show vrrp`를 포함해 VRRP master/backup 상태, 인터페이스, LACP, OSPF, CPU, 메모리, 전원 상태를 점검합니다.
- 첫 수집 결과를 기준 스냅샷으로 저장하고, 이후 수집 결과와 자동 비교합니다.
- 비교 결과를 `긴급`, `주의`, `정보`, `변경없음` 상태로 분류합니다.
- 장비 접속 실패는 여러 명령 실패로 흩어지지 않고 `device_connectivity` 항목 하나로 표시합니다.
- 실제 장비 없이 샘플 스냅샷과 비교 리포트를 생성해 화면 동작을 확인할 수 있습니다.
- GitHub Release의 Windows 통합 ZIP에서는 GUI와 로컬 웹앱을 함께 제공합니다.
- 진단 리포트는 원본 장비 로그 없이 단계별 상태와 `BST-*` 오류 코드만 남깁니다.
- 장비명, 호스트명, IP, password, token, SNMP community 등 민감정보를 자동 마스킹합니다.
- Windows 11에서 Python 설치 없이 실행 가능한 통합 ZIP을 생성합니다.
- 사용자 가이드, 점검 명령어 가이드, 초급 개발자 가이드, 버전 변경내역을 MD/HTML로 제공합니다.

## 일반 사용자 다운로드

GitHub Release에서는 다음 파일 하나만 다운로드하면 됩니다.

```text
backbone_state_tracker_<tag>_windows.zip
```

예시:

```text
backbone_state_tracker_v2026.07.08-104830_windows.zip
```

`Source code (zip)` / `Source code (tar.gz)`는 GitHub가 자동으로 표시하는 소스 아카이브이며 일반 사용자가 실행할 파일이 아닙니다.

ZIP 압축 해제 후:

- GUI: `gui\BackboneStateTracker.exe`를 더블클릭합니다.
- 웹앱: `web\start_webapp.cmd`를 더블클릭합니다.
- 웹앱 기본 주소: `http://127.0.0.1:8765/`
- 웹앱 포트 변경: `web\start_webapp.cmd --port 8777`

최종 사용자용 ZIP에는 CLI 실행 파일과 CLI 전용 안내를 포함하지 않습니다. SHA256 checksum은 Release notes 본문에 기록됩니다.

## 빠른 실행

```powershell
cd "<backbone_state_tracker가 들어있는 폴더>\backbone_state_tracker"
python -m pip install -r requirements.txt
python app.py
```

프로그램 첫 화면인 `장비 설정`에서 백본 3/4호기 접속 정보와 계정을 입력합니다. 비밀번호는 설정 파일이나 리포트에 저장하지 않습니다.

## 실제 장비 없이 확인

GUI의 `샘플 검증 생성` 또는 웹앱의 `샘플 검증 생성` 버튼으로 실제 장비 접속 없이 샘플 스냅샷과 HTML 비교 리포트를 만들 수 있습니다.

## 주요 파일

- `config/devices.example.yaml`: 장비 설정 예시입니다. 실제 `config/devices.yaml`은 로컬 전용이며 Git에 포함하지 않습니다.
- `config/commands.yaml`: 읽기 전용 점검 명령 목록입니다.
- `config/mock_profiles.yaml`: 실제 장비 없이 검증하는 모의 서버 합성 프로파일입니다.
- `outputs/snapshots/`: 수집 스냅샷과 비교 결과가 생성되는 로컬 출력 폴더입니다.
- `RELEASE_NOTES.md`: GitHub Release notes 작성/점검 규칙입니다. 실제 공개 Release body는 GitHub Actions가 자동 생성합니다.
- `docs/USER_GUIDE.md`: 운영자용 사용자 가이드입니다.
- `docs/COMMAND_GUIDE.md`: 명령어별 의미와 확인 포인트입니다.
- `docs/DIAGNOSTIC_MODE_GUIDE.md`: 모의 서버와 현장 진단 모드 사용법입니다.
- `docs/ERROR_CODE_CATALOG.md`: `BST-*` 오류 코드 의미와 1차 조치 방향입니다.
- `docs/DEVELOPER_GUIDE_BEGINNER.md`: 초급 개발자를 위한 구조 설명입니다.
- `docs/VERSION_HISTORY.md`: 버전별 변경내역입니다.
- `docs/RELEASE_CHECKLIST.md`: 사내 반입 전 검증 체크리스트입니다.
- `docs/images/`: 사용자 가이드에 들어가는 화면 이미지입니다.

## README / Release 문서 점검 규칙

코드를 GitHub에 올리거나 Release를 만들기 전에는 문서가 현재 코드와 맞는지 먼저 확인합니다.

1. `README.md`의 설치, 실행, 테스트, 빌드, 릴리스 파일 설명이 실제 스크립트와 맞는지 확인합니다.
2. 릴리스 대상 변경이면 `README.md`, `RELEASE_NOTES.md`, `CHANGELOG.md`를 함께 확인합니다.
3. 새 기능, 삭제된 기능, 바뀐 파일명, 실행 파일명, 폴더 구조, 요구사항, 제한사항이 있으면 README를 수정합니다.
4. 실제 코드에 없는 기능은 문서에 적지 않습니다. 아직 만들지 않은 기능은 `미구현` 또는 `예정`으로 구분합니다.
5. 예시는 `192.0.2.10`, `mock-backbone-3`, `operator` 같은 샘플 값만 사용합니다.
6. 내부 IP, 실제 장비명, 계정, 비밀번호, 고객명, 실제 로그는 README, RELEASE_NOTES, CHANGELOG에 넣지 않습니다.

Git에 커밋하는 파일과 GitHub Release에 올리는 파일은 다릅니다.

- Git에 커밋: 소스 코드, 테스트, `README.md`, `RELEASE_NOTES.md`, `CHANGELOG.md`, `docs/`, `config/*.example.yaml`, 릴리스 스크립트
- Git에 커밋하지 않음: `outputs/`, `dist/`, `build/`, `.venv/`, `config/devices.yaml`, 실제 장비 로그
- 자동 GitHub Release asset: `backbone_state_tracker_<tag>_windows.zip` 1개
- GitHub 자동 `Source code (zip)` / `Source code (tar.gz)`는 실행용 파일이 아닙니다.
- SHA256 checksum은 Release notes 본문에 기록하고 별도 `.sha256` asset은 업로드하지 않습니다.
- Windows 통합 ZIP은 GitHub Actions Windows runner 또는 Windows PC에서 만듭니다. macOS에서 바로 Windows EXE가 만들어진다고 설명하지 않습니다.

## 테스트

```powershell
cd "<backbone_state_tracker가 들어있는 폴더>\backbone_state_tracker"
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
python webapp_launcher.py --smoke
```

## Source ZIP 생성

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

Source ZIP은 `dist\`에 생성됩니다. `.git`, 런타임 출력, 로컬 `config\devices.yaml`, 캐시, build 폴더, 가상환경은 포함하지 않습니다.

## Windows 통합 ZIP 생성

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

생성되는 ZIP 이름 예시:

```text
backbone_state_tracker_v2026.07.08-104830_windows.zip
```

통합 ZIP 내부 구조:

```text
README_START_HERE_KO.txt
gui/
web/
```

사내 환경으로 ZIP을 반입한 뒤에는 구조와 SHA256을 다음 명령으로 검증합니다.

```powershell
Get-FileHash -Algorithm SHA256 .\dist\backbone_state_tracker_v2026.07.08-104830_windows.zip
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v2026.07.08-104830_windows.zip --type windows --require-manifest
```

메일 시스템에서 `.exe`, `.py`, `.ps1`이 포함된 ZIP 업로드를 차단할 수 있습니다. 이 경우 사내 승인된 파일 반입 절차를 사용합니다.
