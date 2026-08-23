# 개발 및 유지관리 기준

이 문서는 백본 상태 추적기를 수정할 때 유지해야 할 구조·안전·검증 원칙을 정리합니다.

## 프로젝트 목적

이 프로젝트는 백본 장비의 상태를 읽기 전용으로 수집하고 작업 전·후 Snapshot을 비교해 운영자가 변경 영향과 복구 상태를 빠르게 확인하도록 돕는 도구입니다.

개발 편의보다 다음 원칙을 우선합니다.

- 장비 구성 무변경
- 비교 결과의 근거 보존
- 접속 실패와 실제 상태 변화 분리
- 계획된 변화와 비예상 변화 구분
- 민감정보 비노출
- 재현 가능한 Mock/자동 검증

## 장비 접근 경계

운영 명령은 `config/commands.yaml`에서 관리합니다.

현재 명령 세트는 상태 조회와 세션 페이징 제어만 사용합니다. 설정 모드 진입 또는 구성 변경 명령을 추가하지 않습니다. `core/command_safety.py`가 전체 명령을 접속 전에 중앙 재검증하며, 이 호출 순서를 우회하는 별도 `ConnectHandler` 경로를 만들지 않습니다.

실제 수집은 `hp_comware` SSH, parseable `known_hosts`, strict host-key 검증, `ssh-rsa` key/pubkey 차단을 함께 요구합니다. 로컬 `config/known_hosts`는 신뢰 자료이므로 Git·fixture·배포 ZIP에 넣지 않습니다.

실제 장비 테스트는 조직 정책과 승인 범위 안에서만 수행하며, 자동 테스트는 실제 운영 장비 접속을 요구하지 않아야 합니다.

## 비교 엔진 원칙

`core/diff_engine.py`의 결과는 단순 문자열 diff보다 운영 의미를 우선합니다.

- 시각, clock, uptime 등 변동성이 높은 값은 의미 없는 변화로 확대하지 않습니다.
- 장비 전체 접속 실패는 `device_connectivity`로 표현하고 하위 명령이 모두 사라졌다는 중복 경고를 만들지 않습니다.
- 비교 시점의 상태 자체가 임계조건을 위반하면 문자열 변화가 없어도 health finding을 생성할 수 있습니다.
- CPU/Memory 등 임계값은 `config/analysis_rules.yaml`에서 관리합니다.
- `expected_changes`는 계획된 변화를 표시하는 메타데이터이며 실제 장애 신호를 숨기지 않습니다.

## 모듈 책임

| 영역 | 책임 |
|---|---|
| `core/collector.py` | 장비 접속과 읽기 전용 명령 수집 |
| `core/command_safety.py` | 중앙 명령 정규화, 장비 타입, known_hosts, SSH 알고리즘 정책 |
| `core/connectivity.py` | 장비 연결 상태를 명령별 실패와 분리 |
| `core/snapshot.py` | 수집 결과 Snapshot 저장/복원 |
| `core/diff_engine.py` | 기준/대상 Snapshot 정규화와 비교 |
| `core/analysis_rules.py` | Finding 및 expected change 규칙 로딩 |
| `core/reporter.py` | 비교 결과와 HTML 보고서 생성 |
| `core/redaction.py` | 공개/진단 정보 마스킹 |
| `core/diagnostics/` | 단계별 진단 이벤트와 `BST-*` 오류 코드 |
| `core/mockserver/` | 실제 장비 없이 접속/수집 경계 재현 |
| `core/gui.py` | Windows GUI 표시와 운영자 조작 |

판정 로직을 GUI에 중복 구현하지 않고 비교/분석 계층의 결과를 표시하도록 유지합니다.

## 민감정보

다음 정보는 Git, 테스트 fixture, Issue/PR, 공개 보고서에 포함하지 않습니다.

- 실제 장비 IP와 Hostname
- 실제 장비 계정과 비밀번호
- 내부 VLAN/라우팅/네트워크 식별정보
- 고객명, 사이트명, 조직명
- 원본 운영 장비 로그
- token, SNMP community, 기타 secret

예시는 `192.0.2.0/24` 등 문서용 주소와 가상 장비명을 사용합니다.

## 변경 후 검증

기본 테스트:

```powershell
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m pip install --require-hashes -r requirements-windows.lock
python -m unittest discover -s tests
python app.py --smoke-check
python webapp_launcher.py --smoke
```

진단 경계에 영향을 주는 경우:

```powershell
python app.py --diagnose --self-check
```

Windows 패키지에 영향을 주는 경우:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

생성 ZIP, SHA-256 sidecar, manifest, CycloneDX SBOM은 반드시 `tools/verify_release_assets.py`로 함께 검증합니다.

## Release 원칙

- 문서/주석 정리만으로 새 Release를 만들지 않습니다.
- 사용자 동작, 수집 명령, 비교 의미, 패키지 구조에 영향을 주는 변경을 의미 있는 단위로 묶습니다.
- 기존 태그와 Release 자산을 덮어쓰지 않습니다.
- 정식 버전은 annotated SemVer tag를 사용하고 네 asset을 함께 검증하며, ZIP build provenance와 SBOM attestation을 게시합니다.
- Windows 실행 패키지는 Windows runner 또는 Windows 환경에서 검증합니다.
- 자동 테스트 결과를 실제 장비/운영 환경 호환성 증거로 과장하지 않습니다.
- Release asset에는 실제 운영정보를 포함하지 않습니다.

상세 기준은 `RELEASE_NOTES.md`와 `docs/RELEASE_CHECKLIST.md`를 따릅니다.

## 문서 구조

README에는 운영자가 프로젝트 성격을 빠르게 이해할 핵심만 둡니다.

- 프로그램 구조: `docs/ARCHITECTURE.md`
- 판정 기준: `docs/CHANGE_VALIDATION_LOGIC.md`
- 검증 범위: `docs/VALIDATION_REPORT.md`
- 사용자 절차: `docs/USER_GUIDE.md`
- 명령 의미: `docs/COMMAND_GUIDE.md`
- 진단 경계: `docs/DIAGNOSTIC_MODE_GUIDE.md`
- 오류 코드: `docs/ERROR_CODE_CATALOG.md`

새 기능을 문서화할 때 실제 코드와 테스트에 존재하는 동작만 기술합니다.
