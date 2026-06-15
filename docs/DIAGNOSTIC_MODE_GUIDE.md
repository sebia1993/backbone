# Backbone State Tracker 진단 모드 가이드

문서 버전: v0.8.57  
작성일: 2026-06-15  
대상: 회사 내부망 PC에서 프로그램을 실행하는 현장 운영자

진단 모드는 실제 장비 원본 로그를 외부로 보내지 않고 문제 원인을 추적하기 위한 기능입니다. 기본 self-check는 장비에 접속하지 않고 앱 리소스, 마스킹 정책, 안전 리포트 생성 흐름만 확인합니다.

## 실행 명령

```powershell
BackboneStateTracker.exe --diagnose --self-check
BackboneStateTracker.exe --explain-code BST-CON-301
```

소스 환경에서는 다음과 같이 실행할 수 있습니다.

```powershell
python app.py --diagnose --self-check
python app.py --explain-code BST-CON-301
```

## Mock 서버 실행

외부 개발 PC에서는 실제 장비 없이 mock 서버로 접속 흐름을 검증합니다. Mock profile은 실제 장비 출력 복사본이 아니라 합성 응답만 사용합니다.

```powershell
BackboneStateTracker.exe --mock-server --protocol telnet --profile normal --self-check
BackboneStateTracker.exe --mock-server --protocol ssh --profile normal --self-check
BackboneStateTracker.exe --mock-server --protocol ssh --profile vrrp_role_change --host 127.0.0.1 --port 2222
```

수집기 통합 검증은 `127.0.0.1`과 mock 서버 포트를 대상 장비로 지정해 수행합니다. 이때 장비명은 `mock-device-a` 같은 합성 이름을 사용합니다.

## 생성 파일

```text
outputs/diagnostics/YYYYMMDD_HHMMSS/
  diagnostic_report.html
  diagnostic_report.json
  diagnostic_ticket.txt
```

| 파일 | 용도 |
| --- | --- |
| `diagnostic_report.html` | 사람이 읽는 안전 리포트 |
| `diagnostic_report.json` | 코드 기반 분석용 구조화 리포트 |
| `diagnostic_ticket.txt` | 메일/메신저로 전달 가능한 최소 정보 |

## 포함되는 정보

- 앱 이름과 버전
- 진단 단계
- 오류 코드
- 등급
- 장비 alias
- 안전한 요약
- 조치 힌트
- `raw_log_included=false`

## 포함되지 않는 정보

- 원본 명령 출력
- 실제 IP
- 실제 호스트명
- 실제 장비명
- 계정, 암호, token, SNMP community
- 내부망 도메인
- raw snapshot 내용

## 외부 분석 요청 절차

1. 회사 내부망 PC에서 `BackboneStateTracker.exe --diagnose --self-check`를 실행합니다.
2. 생성된 `diagnostic_ticket.txt`를 엽니다.
3. 오류 코드와 단계만 외부 개발자에게 전달합니다.
4. 실제 장비명, IP, 호스트명, 원본 출력은 전달하지 않습니다.
5. 외부 개발자는 `--explain-code` 또는 오류 코드 카탈로그로 1차 원인을 안내합니다.

## 예시

```text
Backbone State Tracker v0.8.57 diagnostic ticket
raw_log_included=false

Events:
- BST-CON-301 Critical stage=network status=failed device=DEV-001 summary=TCP connection timed out.
```

위 예시는 실제 IP나 호스트명을 포함하지 않지만, 원인 범위를 관리망/TCP/포트/방화벽/전원으로 좁힐 수 있습니다.
