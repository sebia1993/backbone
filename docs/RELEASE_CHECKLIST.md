# Backbone State Tracker 릴리스 반입 체크리스트

문서 버전: v0.8.20  
작성일: 2026-06-12  
대상: 사외 개발 ZIP을 사내 환경으로 반입해 검증하는 운영자와 인수자

## 1. 수령 파일

```text
backbone_state_tracker_v0.8.20_YYYYMMDD_source.zip
backbone_state_tracker_v0.8.20_YYYYMMDD_source.zip.sha256.txt
backbone_state_tracker_v0.8.20_YYYYMMDD_windows_exe.zip
backbone_state_tracker_v0.8.20_YYYYMMDD_windows_exe.zip.sha256.txt
backbone_state_tracker_v0.8.20_YYYYMMDD_release_manifest.txt
backbone_state_tracker_v0.8.20_YYYYMMDD_verify_release_package.ps1
```

## 2. ZIP 내부 필수 확인

- `PACKAGE_INFO.txt`
- `README.md`
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
- Windows EXE ZIP인 경우 `BackboneStateTracker.exe`, `RUN_FIRST.txt`

## 3. 포함되면 안 되는 항목

- `.git/`
- `outputs/`
- `raw/`
- `dist/`
- `build/`
- `config/devices.yaml`
- `__pycache__/`
- `.pyc`
- `.spec`

## 4. 해시와 manifest 검증

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.20_YYYYMMDD_windows_exe.zip
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v0.8.20_YYYYMMDD_windows_exe.zip --require-manifest
powershell -ExecutionPolicy Bypass -File .\backbone_state_tracker_v0.8.20_YYYYMMDD_verify_release_package.ps1 -Package .\backbone_state_tracker_v0.8.20_YYYYMMDD_windows_exe.zip -RequireManifest
```

검증기는 다음을 확인합니다.

- ZIP 파일명과 sidecar, manifest의 버전/날짜 일치
- ZIP 크기와 SHA256 일치
- ZIP 내부 경로가 `backbone_state_tracker/` 루트 아래에 있는지
- 필수 파일 포함 여부
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

## 6. 메일 업로드 차단 시

일부 메일 시스템은 `.exe`, `.py`, `.ps1`을 포함한 ZIP을 차단할 수 있습니다. 이 경우 ZIP을 메일에 첨부하지 말고 승인된 사내 파일 반입 절차를 사용합니다.
