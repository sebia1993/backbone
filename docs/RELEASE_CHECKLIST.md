# 백본 상태 추적기 운영 환경 배포 체크리스트

문서 버전: v0.9.0
작성일: 2026-08-24
대상: 폐쇄망 또는 운영 환경에 Windows 통합 ZIP을 배포·검증하는 운영자와 인수자

## 1. 수령 파일

```text
backbone_state_tracker_v0.9.0_windows.zip
backbone_state_tracker_v0.9.0_windows.zip.sha256.txt
backbone_state_tracker_v0.9.0_release_manifest.txt
backbone_state_tracker_v0.9.0_sbom.cdx.json
```

GitHub가 자동으로 표시하는 `Source code (zip)` / `Source code (tar.gz)`는 소스 아카이브이며 일반 사용자가 실행할 파일이 아닙니다. 네 자산을 함께 검증하고 ZIP build provenance와 ZIP 대상 SBOM attestation도 확인합니다.

## 2. ZIP 내부 필수 확인

- `README_START_HERE_KO.txt`
- `PACKAGE_INFO.txt`
- `LICENSE` (MIT 허가 고지)
- `gui/BackboneStateTracker.exe`
- `gui/README_GUI_KO.txt`
- `gui/config/commands.yaml`
- `gui/config/devices.example.yaml`
- `gui/config/known_hosts.example`
- `web/start_webapp.cmd`
- `web/runtime/BackboneWebApp.exe`
- `web/README_WEB_KO.txt`
- `web/config/commands.yaml`
- `web/config/devices.example.yaml`
- `web/config/known_hosts.example`

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
- `config/known_hosts`
- `known_hosts.backup`, `credentials.yaml`, `devices.local.yaml` 등 allowlist 밖의 config 파일
- `__pycache__/`
- `.pyc`
- `.spec`
- 루트의 `BackboneStateTracker.exe`
- `RUN_FIRST.txt`
- CLI 실행 파일 또는 CLI 전용 안내 파일
- 별도 `.sha256` 파일
- 소스 `app.py`, `core/`, `tests/`, `tools/`, `docs/`

## 4. 해시와 manifest 검증

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.9.0_windows.zip
python .\tools\verify_release_assets.py --zip .\backbone_state_tracker_v0.9.0_windows.zip --checksum .\backbone_state_tracker_v0.9.0_windows.zip.sha256.txt --manifest .\backbone_state_tracker_v0.9.0_release_manifest.txt --sbom .\backbone_state_tracker_v0.9.0_sbom.cdx.json --version v0.9.0 --repository sebia1993/hpe-comware-change-validator --application backbone_state_tracker --source-commit <40자리커밋>
```

검증기는 다음을 확인합니다.

- 통합 ZIP 존재 여부
- ZIP 크기와 SHA256 일치
- ZIP 내부 경로가 `backbone_state_tracker/` 루트 아래에 있는지
- `README_START_HERE_KO.txt`, `gui/`, `web/` 필수 파일 포함 여부
- GUI 실행 파일 포함 여부
- 웹앱 실행 스크립트와 내장 런타임 포함 여부
- 공유 가능한 `gui/config/*`, `web/config/*` 파일 포함 여부. 실제 `devices.yaml`과 승인 키가 든 `known_hosts`는 제외
- CLI 실행 파일과 CLI 전용 안내 파일 제외 여부
- `outputs/`, `raw/`, `dist/`, `build/`, `.venv/`, `venv/`, `.pytest_cache/` 같은 로컬 산출물/환경 폴더 포함 여부
- 금지 경로 포함 여부
- ZIP 내부 중복 엔트리 여부
- manifest 중복 Package 레코드 여부

## 5. 실행 확인

- 통합 ZIP을 별도 폴더에 해제합니다.
- `README_START_HERE_KO.txt`를 확인합니다.
- 별도 채널로 확인한 fingerprint와 일치하는 키만 `gui\config\known_hosts`에 등록합니다. `known_hosts.example`의 주석만 복사하면 수집은 차단됩니다.
- GUI는 `gui\BackboneStateTracker.exe`를 실행합니다.
- 첫 화면이 `장비 설정`인지 확인합니다.
- 좌측 메뉴가 `장비 설정`, `비교 결과`, `작업 로그` 순서인지 확인합니다.
- `샘플 검증 생성`으로 실제 장비 접속 없이 리포트 생성이 되는지 확인합니다.
- 웹앱은 `web\start_webapp.cmd`를 실행합니다.
- 브라우저에서 `http://127.0.0.1:8765/`가 열리는지 확인합니다.
- 포트 변경이 필요하면 `web\start_webapp.cmd --port 8777` 형식으로 실행합니다.

## 6. UI 마감 확인

- 좌측 내비게이션이 어두운 운영 콘솔 레일이고 현재 메뉴가 teal 계열 배경으로 강조되는지 확인합니다.
- `장비 설정` 화면에서 접속 계정, 대상 장비, 상태 수집 흐름이 위에서 아래로 자연스럽게 이어지는지 확인합니다.
- `비교 결과` 화면에서 `긴급`, `주의`, `정보`, `변경없음` 등급 카드가 상태별 색상과 선택 배경으로 구분되는지 확인합니다.
- 변경 상세 행을 선택했을 때 `선택 변경 맥락` 패널이 등급, 장비, 명령, 유형, 라인을 표시하는지 확인합니다.
- `작업 로그` 화면이 어두운 고정폭 로그 표면으로 표시되고 시간/오류/리포트 경로를 읽기 쉬운지 확인합니다.
- `docs/images/settings-collection.png`, `docs/images/compare-results.png`, `docs/images/work-log.png`는 비식별 합성 UI 자료입니다. v0.9.0 보안 릴리스에서 브라우저 기반 시각 재검증을 수행한 근거로 사용하지 않습니다.

## 7. README / Release 문서 최신화 확인

- `README.md`의 다운로드, GUI 실행, 웹앱 실행, 테스트, 빌드, 사용 방법이 현재 파일과 맞는지 확인합니다.
- `RELEASE_NOTES.md`의 수동 Release notes 형식과 GitHub Release asset 설명이 현재 workflow와 맞는지 확인합니다.
- `CHANGELOG.md`에 사용자에게 보이는 변경사항이 빠지지 않았는지 확인합니다.
- Git에 커밋할 파일과 GitHub Release에 직접 업로드할 ZIP/SHA/manifest/SBOM 4개가 구분되어 있는지 확인합니다.
- Release notes에 `Source code (zip)` / `Source code (tar.gz)`가 실행용 파일이 아니라고 안내되는지 확인합니다.
- CLI 실행 방법이 README, Release notes, ZIP 안내서에 남아 있지 않은지 확인합니다.
- 내부 IP, 실제 장비명, 계정, 비밀번호, 실제 로그, 고객 정보가 문서에 없는지 확인합니다.
- Windows 통합 ZIP은 GitHub Actions Windows runner 또는 Windows PC에서 검증해야 하며, macOS에서 직접 Windows EXE를 만든다고 설명하지 않습니다.

## 8. 폐쇄망·운영 환경 배포

실행 파일이 포함된 ZIP을 운영 환경으로 전달할 때는 조직에서 승인한 소프트웨어 배포·파일 전달 절차를 사용합니다.

- 전달 전 Release notes의 SHA-256을 확인합니다.
- 전달 후 수신 환경에서 SHA-256을 다시 계산합니다.
- 조직 보안 정책에서 허용한 경로에만 압축을 해제합니다.
- 실제 장비 접속 전 `샘플 검증 생성`과 source/package smoke 결과를 먼저 확인합니다.
- 실제 장비 정보는 공개 Issue/PR 또는 외부 문서에 복사하지 않습니다.
- `gh attestation verify`로 다운로드한 ZIP의 저장소와 workflow provenance를 확인합니다.
