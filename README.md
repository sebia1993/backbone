# 백본 상태 추적기

버전: `v0.8.57`

HPE Aruba 계열 백본 3/4호기 상태를 읽기 전용 명령으로 수집하고, 작업 전후 스냅샷을 비교해 장애 징후와 변경점을 추적하는 Windows GUI 도구입니다.

집에서 개발한 뒤 회사 내부망 PC에 반입해 실행하는 상황을 전제로 합니다. 실제 장비 로그, 내부 IP, 호스트명, 계정 정보는 외부로 반출하지 않고, 필요한 경우 모의 서버와 안전 진단 리포트로 검증합니다.

## 주요 기능

- 백본 장비에 SSH로 접속해 `config/commands.yaml`의 읽기 전용 점검 명령만 실행합니다.
- `show vrrp`를 포함해 VRRP master/backup 상태, 인터페이스, LACP, OSPF, CPU, 메모리, 전원 상태를 점검합니다.
- 첫 수집 결과를 기준 스냅샷으로 저장하고, 이후 수집 결과와 자동 비교합니다.
- 비교 결과를 `긴급`, `주의`, `정보`, `변경없음` 상태로 분류합니다.
- 장비 접속 실패는 여러 명령 실패로 흩어지지 않고 `device_connectivity` 항목 하나로 표시합니다.
- 실제 장비 없이 테스트할 수 있는 모의 SSH/Telnet 서버와 합성 프로파일을 제공합니다.
- 회사 현장에서 `--diagnose --self-check`로 설정, 모의 장비 프로파일, 문서 포함 여부를 안전하게 점검할 수 있습니다.
- 진단 리포트는 원본 장비 로그 없이 단계별 상태와 `BST-*` 오류 코드만 남깁니다.
- 장비명, 호스트명, IP, password, token, SNMP community 등 민감정보를 자동 마스킹합니다.
- Windows 11에서 Python 설치 없이 실행 가능한 단독 EXE ZIP을 생성합니다.
- 사용자 가이드, 점검 명령어 가이드, 초급 개발자 가이드, 버전 변경내역을 MD/HTML로 제공합니다.

## 빠른 실행

```powershell
cd "<backbone_state_tracker가 들어있는 폴더>\backbone_state_tracker"
python -m pip install -r requirements.txt
python app.py
```

프로그램 첫 화면인 `장비 설정`에서 백본 3/4호기 접속 정보와 계정을 입력합니다. 비밀번호는 설정 파일이나 리포트에 저장하지 않습니다.

## 실제 장비 없이 확인

모의 서버 자체 점검:

```powershell
python app.py --mock-server --protocol ssh --profile normal --self-check
python app.py --mock-server --protocol telnet --profile normal --self-check
```

회사 현장 진단 자체 점검:

```powershell
python app.py --diagnose --self-check
python app.py --explain-code BST-CON-301
```

진단 결과는 `outputs\diagnostics\` 아래에 HTML, JSON, 진단 티켓 텍스트로 생성됩니다. 이 리포트는 원본 장비 출력과 실제 내부 주소를 포함하지 않도록 설계되어 있습니다.

## 주요 파일

- `config/devices.example.yaml`: 장비 설정 예시입니다. 실제 `config/devices.yaml`은 로컬 전용이며 Git에 포함하지 않습니다.
- `config/commands.yaml`: 읽기 전용 점검 명령 목록입니다.
- `config/mock_profiles.yaml`: 실제 장비 없이 검증하는 모의 서버 합성 프로파일입니다.
- `outputs/snapshots/`: 수집 스냅샷과 비교 결과가 생성되는 로컬 출력 폴더입니다.
- `docs/USER_GUIDE.md`: 운영자용 사용자 가이드입니다.
- `docs/COMMAND_GUIDE.md`: 명령어별 의미와 확인 포인트입니다.
- `docs/DIAGNOSTIC_MODE_GUIDE.md`: 모의 서버와 현장 진단 모드 사용법입니다.
- `docs/ERROR_CODE_CATALOG.md`: `BST-*` 오류 코드 의미와 1차 조치 방향입니다.
- `docs/DEVELOPER_GUIDE_BEGINNER.md`: 초급 개발자를 위한 구조 설명입니다.
- `docs/VERSION_HISTORY.md`: 버전별 변경내역입니다.
- `docs/RELEASE_CHECKLIST.md`: 사내 반입 전 검증 체크리스트입니다.
- `docs/images/`: 사용자 가이드에 들어가는 화면 이미지입니다.

## 테스트

```powershell
cd "<backbone_state_tracker가 들어있는 폴더>\backbone_state_tracker"
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
```

## Source ZIP 생성

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

Source ZIP은 `dist\`에 생성됩니다. `.git`, 런타임 출력, 로컬 `config\devices.yaml`, 캐시, build 폴더, 가상환경은 포함하지 않습니다.

## Windows EXE ZIP 생성

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

생성되는 ZIP 이름 예시:

```text
backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip
```

사내 환경으로 ZIP을 반입한 뒤에는 다음 명령으로 검증합니다.

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip --require-manifest
powershell -ExecutionPolicy Bypass -File .\backbone_state_tracker_v0.8.57_YYYYMMDD_verify_release_package.ps1 -Package .\backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip -RequireManifest
```

메일 시스템에서 `.exe`, `.py`, `.ps1`이 포함된 ZIP 업로드를 차단할 수 있습니다. 이 경우 사내 승인된 파일 반입 절차를 사용합니다.
