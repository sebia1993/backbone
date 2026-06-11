# Backbone State Tracker 릴리스 반입 체크리스트

문서 버전: v0.8.9
작성일: 2026-06-12  
대상: 사외 개발 ZIP을 사내 환경으로 반입해 검증하는 운영자와 인수자

## 1. 핵심 확인

- `dist/latest/` 또는 `dist/CURRENT_RELEASE.txt`가 반입할 최신 버전을 가리키는지 먼저 확인합니다.
- Windows 실행본이 필요하면 `*_windows_exe.zip`을 사용합니다. `*_source.zip`에는 실행 파일이 포함되지 않습니다.
- ZIP 파일과 같은 폴더에 동일한 이름의 `.sha256.txt`, 같은 버전의 `*_release_manifest.txt`, `*_verify_release_package.ps1`가 있는지 확인합니다.
- ZIP 내부에는 `PACKAGE_INFO.txt`, README, CHANGELOG, `config/commands.yaml`, `config/devices.example.yaml`, `docs/` 가이드 문서가 있어야 합니다.
- ZIP 내부에 `config/devices.yaml`, `outputs/`, `raw/`, `.git/`, `build/`, 캐시 파일이 있으면 반입하지 않습니다.

## 2. 파일 세트 확인

반입 폴더에는 아래 파일 세트가 함께 있어야 합니다.

```text
backbone_state_tracker_v0.8.9_YYYYMMDD_source.zip
backbone_state_tracker_v0.8.9_YYYYMMDD_source.zip.sha256.txt
backbone_state_tracker_v0.8.9_YYYYMMDD_windows_exe.zip
backbone_state_tracker_v0.8.9_YYYYMMDD_windows_exe.zip.sha256.txt
backbone_state_tracker_v0.8.9_YYYYMMDD_release_manifest.txt
backbone_state_tracker_v0.8.9_YYYYMMDD_verify_release_package.ps1
CURRENT_RELEASE.txt
```

소스 ZIP만 전달하는 경우에는 Windows 실행 파일이 없습니다. 현장 운영자가 바로 실행해야 하는 배포물은 Windows EXE ZIP입니다.

## 3. 무결성 확인

PowerShell에서 ZIP 해시를 확인합니다.

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.9_YYYYMMDD_windows_exe.zip
```

출력된 SHA256 값이 같은 이름의 `.sha256.txt` 또는 `*_release_manifest.txt`에 기록된 값과 일치해야 합니다.
검증기는 ZIP 파일명 버전, `.sha256.txt`의 `Version`, `*_release_manifest.txt`의 `Version`과 `Date stamp`도 함께 비교합니다.

소스 폴더가 함께 있는 환경에서는 Python 검증기를 실행합니다.

```powershell
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v0.8.9_YYYYMMDD_windows_exe.zip --require-manifest
```

ZIP 파일과 검증 스크립트만 있는 환경에서는 독립 PowerShell 검증기를 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\backbone_state_tracker_v0.8.9_YYYYMMDD_verify_release_package.ps1 -Package .\backbone_state_tracker_v0.8.9_YYYYMMDD_windows_exe.zip -RequireManifest
```

정상 결과는 `Verification OK`입니다.

## 4. ZIP 내부 확인

Windows EXE ZIP을 임시 폴더에 압축 해제한 뒤 아래 항목을 확인합니다.

- `BackboneStateTracker.exe`가 있습니다.
- `RUN_FIRST.txt`가 있습니다.
- `PACKAGE_INFO.txt`가 있습니다.
- `docs/USER_GUIDE.md`와 `docs/USER_GUIDE.html`이 있습니다.
- `docs/COMMAND_GUIDE.md`와 `docs/COMMAND_GUIDE.html`이 있습니다.
- `docs/DEVELOPER_GUIDE_BEGINNER.md`와 `docs/DEVELOPER_GUIDE_BEGINNER.html`이 있습니다.
- `docs/VERSION_HISTORY.md`와 `docs/VERSION_HISTORY.html`이 있습니다.
- `docs/RELEASE_CHECKLIST.md`와 `docs/RELEASE_CHECKLIST.html`이 있습니다.
- `config/devices.example.yaml`은 있지만 `config/devices.yaml`은 없습니다.

## 5. 실행 확인

압축을 해제한 폴더에서 실행 파일을 확인합니다.

```powershell
.\BackboneStateTracker.exe --smoke-check
```

GUI로 실행할 때는 장비 IP, 계정, 비밀번호를 운영자가 직접 입력합니다. 비밀번호는 프로그램 설정 파일, 보고서, 배포 ZIP에 저장하지 않습니다.

## 6. 운영 전 확인

- 실제 백본 3/4호기 접속 전 `설정 점검`을 실행해 장비명, IP, 포트, 명령어 구성을 확인합니다.
- 작업 전 기준 스냅샷, 백본3 OFF 중 스냅샷, 복구 후 스냅샷 순서로 수집합니다.
- 장비 한 대가 접속되지 않아도 비교 결과의 `device_connectivity` 항목으로 추적합니다.
- 공유용 ZIP은 redacted 보고서와 가이드만 포함하며 raw 원본 출력은 포함하지 않습니다.
- raw 출력은 운영 증거이므로 외부 공유 전 별도로 민감정보 포함 여부를 확인합니다.

## 7. 실패 시 조치

- SHA256이 다르면 ZIP을 사용하지 말고 원본 배포물을 다시 전달받습니다.
- `Missing required ZIP entry`가 나오면 ZIP 생성 또는 전달 과정에서 파일이 빠진 것입니다.
- `Forbidden ZIP entry found`가 나오면 로컬 설정, 출력, 빌드 산출물, raw 원본이 섞인 것입니다.
- `version mismatch` 또는 `date mismatch`가 나오면 ZIP, `.sha256.txt`, `release_manifest.txt` 중 서로 다른 버전 파일이 섞인 것입니다.
- EXE ZIP이 메일에 업로드되지 않으면 사내 승인된 파일 반입 경로를 사용합니다.
