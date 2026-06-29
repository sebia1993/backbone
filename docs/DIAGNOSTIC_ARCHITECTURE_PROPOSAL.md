# 백본 상태 추적기 진단/모의 서버 설계 제안

문서 상태: 구현 전 설계안  
대상 버전: v0.8.57  
작성일: 2026-06-15  
목표: 외부 개발 PC에서 실제 장비 정보 없이 검증하고, 회사 내부망 PC에서는 원본 로그를 외부로 반출하지 않고 오류 코드만으로 원인 분석이 가능하게 만든다.

## 1. 설계 원칙

- 실제 장비 로그, 샘플 출력, IP, 호스트명, 계정 정보는 외부 개발 환경으로 가져오지 않는다.
- 외부 개발 환경에서는 모의 SSH/Telnet 서버와 합성 응답만 사용한다.
- 회사 내부망 현장에서는 진단 모드가 단계별 상태와 오류 코드만 남기고, 원본 명령 출력은 안전 리포트에서 제외한다.
- 외부 전달용 자료는 `오류 코드`, `단계`, `장비 alias`, `조치 힌트`, `앱 버전`, `패키지 해시`만 포함한다.
- 모든 텍스트 저장 지점은 민감정보 마스킹을 기본값으로 사용한다.
- Windows 11 반입 ZIP은 Python 설치 없이 `BackboneStateTracker.exe` 단독 실행이 가능해야 한다.

## 2. 제안 폴더 구조

```text
backbone_state_tracker/
  core/
    diagnostics/
      __init__.py
      codes.py              # 오류 코드 카탈로그와 설명/조치 매핑
      events.py             # 단계별 진단 이벤트 데이터 모델
      probes.py             # 설정, EXE 리소스, 쓰기 권한, 네트워크 probe
      recorder.py           # 이벤트 수집, 장비 alias, 민감정보 마스킹
      report.py             # 원본 로그 없는 HTML/JSON/TXT 안전 리포트 생성
      runner.py             # 회사 현장 진단 모드 실행 흐름
    mockserver/
      __init__.py
      profiles.py           # 모의 장비 프로파일 로드와 명령별 응답 매핑
      ssh_server.py         # 로컬 SSH 모의 서버
      telnet_server.py      # 로컬 Telnet 모의 서버
      runner.py             # 모의 서버 시작/중지 CLI 진입점
  config/
    mock_profiles.yaml      # 정상/장애/VRRP/CPU/Memory 합성 시나리오
  docs/
    DIAGNOSTIC_MODE_GUIDE.md
    DIAGNOSTIC_MODE_GUIDE.html
    ERROR_CODE_CATALOG.md
    ERROR_CODE_CATALOG.html
  tests/
    test_diagnostics_codes.py
    test_diagnostics_report.py
    test_mock_profiles.py
    test_mock_telnet_server.py
    test_mock_ssh_server.py
    test_safe_report_redaction.py
```

기존 모듈과의 관계:

- `core/collector.py`: 실제 수집 로직은 유지하고, mock 서버도 동일한 접속 흐름으로 검증한다.
- `core/redaction.py`: 기존 마스킹을 확장해 IP, 호스트명, 장비명 alias까지 처리한다.
- `core/preflight.py`: 현장 진단 모드의 설정/명령 안전성 probe에서 재사용한다.
- `core/reporter.py`: 원본 출력 포함 비교 리포트는 유지하되, 진단 모드는 별도 `diagnostics/report.py`에서 안전 리포트를 만든다.
- `tools/build_windows_exe.ps1`: 모의 장비 프로파일, 진단 문서, 오류 코드 카탈로그가 EXE ZIP에 포함되도록 확장한다.

## 3. 실행 모드

### 3.1 외부 개발 PC mock 검증

목적: 실제 장비 없이 SSH/Telnet 접속, 로그인, 명령 실행, 타임아웃, 장애 응답을 검증한다.

예상 명령:

```powershell
BackboneStateTracker.exe --mock-server --profile normal --ssh-port 2222 --telnet-port 2323
BackboneStateTracker.exe --mock-server --profile vrrp_role_change --ssh-port 2222
```

모의 서버 프로파일 후보:

| Profile | 목적 |
| --- | --- |
| `normal` | 모든 명령 정상 응답 |
| `backbone3_down` | 한 장비 접속 실패 시나리오 |
| `auth_failed` | 인증 실패 |
| `command_timeout` | 특정 명령 지연/타임아웃 |
| `vrrp_role_change` | VRRP Master/Backup 변경 |
| `cpu_warning` | CPU 50~69% 주의 |
| `cpu_critical` | CPU 70% 이상 긴급 |
| `memory_warning` | FreeRatio 31~40% 주의 |
| `memory_critical` | FreeRatio 30% 이하 긴급 |
| `power_abnormal` | Power State가 Normal이 아닌 긴급 |

mock 응답은 실제 장비 출력 복사본이 아니라 합성 템플릿만 사용한다. 주소는 `127.0.0.1`, `192.0.2.0/24` 같은 문서용 대역만 사용한다.

### 3.2 회사 현장 진단 모드

목적: 내부망 PC에서 문제 원인을 단계별로 확인하되, 외부 전달 가능한 산출물에는 원본 로그를 넣지 않는다.

예상 명령:

```powershell
BackboneStateTracker.exe --diagnose
BackboneStateTracker.exe --diagnose --safe-report
BackboneStateTracker.exe --explain-code BST-CON-301
```

진단 단계:

| 단계 | 확인 내용 | 원본 로그 저장 |
| --- | --- | --- |
| `startup` | EXE 버전, 실행 경로, 필수 리소스 존재 | 없음 |
| `config` | `commands.yaml`, 장비 설정 형식, 포트 범위 | 없음 |
| `security` | 마스킹 정책, 저장 금지 경로, 반출 리포트 범위 | 없음 |
| `preflight` | 읽기 전용 명령 여부, 위험 명령 차단 | 없음 |
| `network` | TCP 연결 가능 여부, SSH/Telnet 배너 단계 | 없음 |
| `auth` | 인증 성공/실패 코드화 | 없음 |
| `collect` | 명령 실행 성공/실패, 시간 초과 | 원본 출력 제외 |
| `report` | 안전 리포트 생성 여부 | 없음 |
| `package` | EXE ZIP 리소스, manifest, SHA256 확인 | 없음 |

## 4. 진단 이벤트 모델

진단 이벤트는 사람이 읽는 메시지보다 오류 코드와 단계가 우선이다.

```json
{
  "timestamp": "2026-06-15T09:30:00+09:00",
  "app_version": "0.9.0",
  "stage": "network",
  "code": "BST-CON-301",
  "severity": "Critical",
  "device_alias": "DEV-001",
  "status": "failed",
  "summary": "TCP 연결 시간이 초과됐습니다.",
  "action_hint": "장비 전원, 관리망, 방화벽, 포트 번호를 현장에서 확인하세요.",
  "safe_detail": "connect_timeout_seconds=30",
  "raw_log_included": false
}
```

장비명/IP/호스트명은 리포트에서 `DEV-001`, `DEV-002`로 치환한다. alias 원본 매핑은 내부 PC의 런타임 폴더에만 남기거나, 기본값으로 저장하지 않는다.

## 5. 오류 코드 체계

오류 코드는 `BST-영역-번호` 형식으로 고정한다.

| Prefix | 영역 | 예시 |
| --- | --- | --- |
| `BST-CFG-1xxx` | 설정 파일, 장비, 명령 정의 | `BST-CFG-101 DEVICE_CONFIG_MISSING` |
| `BST-SEC-2xxx` | 민감정보, 마스킹, 반출 안전성 | `BST-SEC-201 SECRET_REDACTED` |
| `BST-CON-3xxx` | SSH/Telnet/TCP 접속 | `BST-CON-301 TCP_TIMEOUT` |
| `BST-COL-4xxx` | 명령 실행, 타임아웃, 부분 수집 | `BST-COL-401 COMMAND_TIMEOUT` |
| `BST-DIF-5xxx` | 스냅샷 비교와 판정 | `BST-DIF-501 BASELINE_NOT_FOUND` |
| `BST-REP-6xxx` | 리포트 생성과 공유 ZIP | `BST-REP-601 SAFE_REPORT_CREATED` |
| `BST-PKG-7xxx` | EXE 패키징과 리소스 | `BST-PKG-701 EXE_RESOURCE_MISSING` |
| `BST-MOCK-8xxx` | mock 서버와 profile | `BST-MOCK-801 MOCK_PROFILE_NOT_FOUND` |
| `BST-SYS-9xxx` | OS, 권한, 경로, 런타임 | `BST-SYS-901 OUTPUT_PATH_DENIED` |

초기 필수 코드:

| Code | 이름 | 등급 | 의미 | 1차 조치 |
| --- | --- | --- | --- | --- |
| `BST-CFG-101` | `DEVICE_CONFIG_MISSING` | 긴급 | 대상 장비 설정이 없음 | 장비 설정 화면에서 대상 장비를 추가 |
| `BST-CFG-102` | `COMMAND_CONFIG_MISSING` | 긴급 | 명령 설정 파일 없음 | ZIP에 `config/commands.yaml` 포함 여부 확인 |
| `BST-CFG-121` | `UNSAFE_COMMAND_BLOCKED` | 긴급 | 쓰기/변경성 명령 차단 | 명령 목록에서 해당 명령 제거 |
| `BST-SEC-201` | `SECRET_REDACTED` | 정보 | 민감정보가 마스킹됨 | 정상 동작, 원문 공유 금지 |
| `BST-SEC-211` | `DEVICE_ALIAS_APPLIED` | 정보 | 장비명이 alias로 치환됨 | 외부 공유 시 alias만 전달 |
| `BST-CON-301` | `TCP_TIMEOUT` | 긴급 | TCP 연결 시간 초과 | 관리망, 방화벽, 포트, 전원 확인 |
| `BST-CON-302` | `SSH_AUTH_FAILED` | 긴급 | SSH 인증 실패 | 계정/암호/권한 확인 |
| `BST-CON-303` | `TELNET_LOGIN_FAILED` | 긴급 | Telnet 로그인 실패 | 계정/암호/접속 방식 확인 |
| `BST-CON-304` | `CONNECTION_REFUSED` | 긴급 | 원격 포트 연결 거부 | 서비스 활성화와 포트 확인 |
| `BST-COL-401` | `COMMAND_TIMEOUT` | 주의 | 명령 응답 시간 초과 | 장비 부하 또는 timeout 값 확인 |
| `BST-COL-411` | `DEVICE_PARTIAL_COLLECTION` | 주의 | 일부 명령만 수집됨 | 실패한 명령 코드 확인 |
| `BST-REP-601` | `SAFE_REPORT_CREATED` | 정보 | 안전 리포트 생성 완료 | 외부 공유 가능 파일 확인 |
| `BST-PKG-701` | `EXE_RESOURCE_MISSING` | 긴급 | EXE 실행 리소스 누락 | ZIP 재빌드 또는 반입 파일 확인 |
| `BST-MOCK-801` | `MOCK_PROFILE_NOT_FOUND` | 긴급 | 모의 장비 프로파일 없음 | 프로파일 이름과 YAML 포함 여부 확인 |
| `BST-SYS-901` | `OUTPUT_PATH_DENIED` | 긴급 | 출력 경로 쓰기 실패 | 폴더 권한 또는 보안 정책 확인 |

## 6. 안전 리포트 설계

생성 파일:

```text
outputs/diagnostics/YYYYMMDD_HHMMSS/
  diagnostic_report.html       # 내부/외부 공유용 안전 리포트
  diagnostic_report.json       # 오류 코드 기반 구조화 리포트
  diagnostic_ticket.txt        # 메일/메신저로 전달 가능한 최소 정보
```

포함 허용:

- 앱 이름과 버전
- 실행 OS와 EXE/소스 실행 여부
- 진단 단계
- 오류 코드
- 등급
- 장비 alias
- 안전한 요약 메시지
- 조치 힌트
- 패키지 manifest/SHA256 상태

포함 금지:

- 원본 명령 출력
- 실제 IP, 호스트명, 장비명
- 계정, 암호, 토큰, SNMP community
- 고객명, 위치명, 내부망 도메인
- raw snapshot 파일 경로

## 7. 마스킹 정책

기존 `core/redaction.py`를 확장해 다음을 기본 마스킹 대상으로 한다.

| 유형 | 처리 |
| --- | --- |
| Password, token, API key, Authorization header | `***` |
| SNMP community | `***` |
| URL credential | `://user:***@host` |
| 실제 IPv4/IPv6 | `IP-ALIAS-001` |
| 호스트명/FQDN | `HOST-ALIAS-001` |
| 장비명 | `DEV-001` |
| 원본 파일 경로 | `PATH-REDACTED` |

마스킹은 리포트 생성 직전에만 수행하지 않고, 진단 이벤트 기록 시점부터 적용한다.

## 8. Windows EXE 패키징 기준

Windows 11 현장 PC에서는 다음만으로 실행되어야 한다.

```text
backbone_state_tracker/
  BackboneStateTracker.exe
  RUN_FIRST.txt
  PACKAGE_INFO.txt
  config/
  docs/
```

추가 패키징 기준:

- `config/mock_profiles.yaml` 포함
- `docs/DIAGNOSTIC_MODE_GUIDE.*` 포함
- `docs/ERROR_CODE_CATALOG.*` 포함
- `diagnostic_report.html/json/txt`는 런타임 생성물이므로 ZIP에는 포함하지 않음
- `config/devices.yaml`, `outputs/`, raw snapshot은 ZIP에서 제외
- EXE smoke check에 `--diagnose --dry-run` 또는 `--diagnose --self-check`를 추가

## 9. 구현 단계 제안

### v0.8.57-alpha1: 오류 코드와 안전 리포트 기반

- `core/diagnostics/codes.py`, `events.py`, `recorder.py`, `report.py`
- `--diagnose --self-check`
- 원본 로그 없는 HTML/JSON/TXT 리포트
- 오류 코드 카탈로그 문서

### v0.8.57-alpha2: 모의 Telnet 서버

- `core/mockserver/telnet_server.py`
- `config/mock_profiles.yaml`
- Telnet 기반 정상/장애 profile 테스트

### v0.8.57-alpha3: 모의 SSH 서버

- `paramiko` 기반 모의 SSH 서버
- SSH 인증 실패, 접속 거부, 명령 timeout profile
- 기존 collector와 mock 서버 연동 테스트

### v0.8.57-beta1: GUI 통합

- 도움말 메뉴에 진단 모드/오류 코드 문서 연결
- GUI에서 안전 진단 실행 버튼 제공
- 진단 리포트 폴더 열기

### v0.8.57: 패키징과 반입 검증

- source ZIP / windows EXE ZIP 재생성
- release verifier에 진단 문서, 모의 장비 프로파일, EXE self-check 포함 여부 검증
- 사용자 가이드와 초급 개발자 가이드 갱신

## 10. 구현 전 결정사항

1. 모의 SSH 서버 의존성은 `paramiko`를 사용할지 확인이 필요하다. 이미 Netmiko가 Paramiko 계열을 사용하므로 패키징 충돌 가능성은 낮다.
2. Telnet 지원은 표준 socket 기반으로 구현하는 것이 안전하다. Python `telnetlib` 의존은 피한다.
3. 진단 리포트는 기본적으로 외부 공유 가능 수준으로 만들고, 원본 로그 포함 옵션은 제공하지 않는 것을 권장한다.
4. 장비 alias 원본 매핑 파일은 기본 저장하지 않는 방향을 권장한다. 현장 사용자가 필요할 때만 별도 내부 전용 파일로 저장하게 한다.
5. 기능 규모가 크므로 릴리스는 `v0.8.57` 계열로 올리는 것이 적절하다.
