# 백본 상태 추적기 오류 코드 카탈로그

문서 버전: v0.8.57  
작성일: 2026-06-15  
대상: 현장 운영자, 외부 개발자, 장애 분석 담당자

이 문서는 원본 장비 로그 없이 오류 코드만으로 원인 범위를 좁히기 위한 기준입니다. 외부로 문의할 때는 실제 IP, 호스트명, 장비명, 계정, 원본 명령 출력을 보내지 말고 `diagnostic_ticket.txt`의 코드와 단계만 전달합니다.

## 코드 형식

```text
BST-AREA-NNN
```

| 구간 | 의미 |
| --- | --- |
| `BST-CFG-1xxx` | 설정 파일, 대상 장비, 명령 정의 |
| `BST-SEC-2xxx` | 민감정보, 마스킹, 외부 반출 안전성 |
| `BST-CON-3xxx` | SSH/Telnet/TCP 접속 |
| `BST-COL-4xxx` | 명령 실행, 수집 타임아웃, 부분 수집 |
| `BST-DIF-5xxx` | 스냅샷 비교와 기준 스냅샷 |
| `BST-REP-6xxx` | 안전 리포트 생성 |
| `BST-PKG-7xxx` | Windows EXE 패키지와 포함 리소스 |
| `BST-MOCK-8xxx` | 모의 서버와 프로파일 |
| `BST-SYS-9xxx` | OS, 권한, 출력 경로, 런타임 |

## 코드 목록

| Code | 이름 | 등급 | 단계 | 의미 | 1차 조치 |
| --- | --- | --- | --- | --- | --- |
| `BST-CFG-101` | `DEVICE_CONFIG_MISSING` | 긴급 | config | 사용 가능한 대상 장비가 없습니다. | 장비 설정 화면에서 대상 장비를 1대 이상 추가합니다. |
| `BST-CFG-102` | `COMMAND_CONFIG_MISSING` | 긴급 | config | 명령 설정 파일이 없습니다. | 반입 ZIP에 `config/commands.yaml`이 포함됐는지 확인합니다. |
| `BST-CFG-121` | `UNSAFE_COMMAND_BLOCKED` | 긴급 | config | 쓰기/변경 가능성이 있는 명령이 차단됐습니다. | 명령 목록에서 해당 명령을 제거하고 읽기 전용 명령만 사용합니다. |
| `BST-SEC-201` | `SECRET_REDACTED` | 정보 | security | 민감정보가 저장 전 마스킹됐습니다. | 정상 동작입니다. 생성된 안전 리포트만 공유합니다. |
| `BST-SEC-211` | `DEVICE_ALIAS_APPLIED` | 정보 | security | 장비, 호스트, 주소 값이 alias로 치환됐습니다. | 외부 문의 시 alias만 전달하고 실제 매핑은 내부에만 둡니다. |
| `BST-CON-301` | `TCP_TIMEOUT` | 긴급 | connection | TCP 연결 시간이 초과됐습니다. | 장비 전원, 관리망, 방화벽, 포트 번호를 현장에서 확인합니다. |
| `BST-CON-302` | `SSH_AUTH_FAILED` | 긴급 | connection | SSH 인증에 실패했습니다. | 계정, 암호, SSH 권한, 장비 로그인 정책을 확인합니다. |
| `BST-CON-303` | `TELNET_LOGIN_FAILED` | 긴급 | connection | Telnet 로그인에 실패했습니다. | 계정, 암호, Telnet 접근 정책, 접속 방식을 확인합니다. |
| `BST-CON-304` | `CONNECTION_REFUSED` | 긴급 | connection | 원격 포트가 연결을 거부했습니다. | SSH/Telnet 서비스 활성화와 포트 번호를 확인합니다. |
| `BST-COL-401` | `COMMAND_TIMEOUT` | 주의 | collection | 명령이 제한시간 안에 응답하지 않았습니다. | 장비 부하, 명령 실행 시간, timeout 값을 확인합니다. |
| `BST-COL-411` | `DEVICE_PARTIAL_COLLECTION` | 주의 | collection | 일부 명령만 수집됐습니다. | 실패한 명령 코드와 장비 상태를 확인한 뒤 재진단합니다. |
| `BST-DIF-501` | `BASELINE_NOT_FOUND` | 주의 | diff | 비교 기준 스냅샷이 없습니다. | 작업 전 기준 스냅샷을 먼저 생성합니다. |
| `BST-REP-601` | `SAFE_REPORT_CREATED` | 정보 | report | 원본 출력 없는 안전 리포트가 생성됐습니다. | 외부 분석 요청 시 진단 티켓 또는 안전 리포트를 전달합니다. |
| `BST-PKG-701` | `EXE_RESOURCE_MISSING` | 긴급 | package | EXE 실행에 필요한 리소스가 없습니다. | Windows EXE ZIP을 재빌드/재반입하고 manifest를 검증합니다. |
| `BST-MOCK-801` | `MOCK_PROFILE_NOT_FOUND` | 긴급 | mock | 요청한 모의 장비 프로파일을 찾을 수 없습니다. | 프로파일 이름과 `config/mock_profiles.yaml` 포함 여부를 확인합니다. |
| `BST-SYS-900` | `DIAGNOSTIC_SELF_CHECK_STARTED` | 정보 | system | 진단 자체 점검이 시작됐습니다. | 이어지는 이벤트를 확인합니다. |
| `BST-SYS-901` | `OUTPUT_PATH_DENIED` | 긴급 | system | 진단 출력 경로에 쓸 수 없습니다. | 승인된 쓰기 가능 폴더에서 실행하거나 폴더 권한을 확인합니다. |

## 외부 문의 예시

```text
앱: 백본 상태 추적기 v0.8.57
코드: BST-CON-301
단계: network
장비 alias: DEV-001
상태: failed
원본 로그 포함=false
```

이 정도 정보면 실제 장비 로그 없이도 1차 원인을 `관리망/TCP/포트/방화벽/전원` 범위로 좁힐 수 있습니다.

