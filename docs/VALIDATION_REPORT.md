# 검증 보고서

이 문서는 백본 상태 추적기의 자동 검증, Mock 검증, Windows 패키지 검증, 실제 운영 환경 검증을 서로 다른 증거 수준으로 구분합니다.

실제 장비 IP, Hostname, 계정, 내부 VLAN/라우팅 정보, 원본 장비 로그는 공개 저장소에 기록하지 않습니다.

## 현재 공개 검증 범위

| 검증 영역 | 상태 | 공개 근거 |
|---|---|---|
| Snapshot 저장/복원 | ✅ 자동 검증 | `tests/` |
| 기준/대상 Snapshot 비교 | ✅ 자동 검증 | `tests/`, `core/diff_engine.py` |
| 변동성 값 정규화 | ✅ 자동 검증 | Diff Engine 테스트 |
| 장비 접속 실패 단일화 | ✅ 자동 검증 | Connectivity/Diff 테스트 |
| Interface/LACP/OSPF/VRRP 판정 | ✅ 자동 검증 | Analysis/Diff 테스트 |
| CPU/Memory 임계값 판정 | ✅ 자동 검증 | Analysis rule 테스트 |
| Expected Change 구분 | ✅ 자동 검증 | Rule/Diff 테스트 |
| 중앙 명령 fail-closed 경계 | ✅ 자동 검증 | `tests/test_collection_security.py` |
| known_hosts 선파싱/0회 접속 | ✅ 자동 검증 | 없음·주석-only·malformed 회귀 테스트 |
| strict SSH/ssh-rsa 차단 | ✅ 자동 검증 | ConnectHandler 인자 계약 테스트 |
| Mock SSH/Telnet 경계 | ✅ 자동 검증 | ECDSA SSH + 명시적 RejectPolicy, Telnet mock |
| GUI Source smoke | ✅ PR Validation | `python app.py --smoke-check` |
| Webapp Source smoke | ✅ PR Validation | `python webapp_launcher.py --smoke` |
| Windows 통합 ZIP 생성 | ✅ GitHub Actions | Windows runner |
| Windows ZIP manifest/SHA 검증 | ✅ GitHub Actions | Package/asset verifier |
| CycloneDX SBOM | ✅ GitHub Actions | CycloneDX 1.6 `serialNumber`와 runtime lock 20개 전체 name/version 검증 |
| Build provenance/SBOM 증명 | ✅ GitHub Actions | GitHub artifact attestation |
| 실제 장비/OS별 출력 호환성 | 별도 현장 증거 | 공개 원문은 저장하지 않음 |

> 자동 테스트와 Mock 결과가 실제 백본 장비에서의 운영 검증을 대체한다고 표현하지 않습니다.

## 검증 대상 기능

### 수집

| 항목 | 합격 기준 |
|---|---|
| 장비 접속 | 허용된 방식으로 세션 수립 또는 명확한 connectivity failure |
| 명령 allowlist | `commands.yaml`에 정의된 상태 조회 범위만 실행 |
| 명령 중앙 재검증 | NFKC/ASCII/길이/메타문자/전체 allowlist 검사가 모든 접속 전에 완료됨 |
| 장비 타입 | SSH 기반 `hp_comware` 외 입력은 접속 전에 실패 |
| 호스트 키 | parseable `known_hosts`에 유효 키가 없으면 접속 전에 실패 |
| SSH 알고리즘 | strict host-key와 `ssh-rsa` key/pubkey 차단 인자를 강제 |
| 페이징 처리 | 긴 출력이 중간에서 잘리지 않도록 session setup 수행 |
| 명령 실패 | 실패한 명령의 상태와 오류가 다른 정상 결과를 오염시키지 않음 |
| 장비 전체 접속 실패 | 하위 명령 실패를 중복 finding으로 증폭하지 않음 |
| Timeout | 개별 명령이 무한 대기하지 않음 |

### Snapshot

| 항목 | 합격 기준 |
|---|---|
| 기준 Snapshot | 작업 전 수집 결과가 재사용 가능한 형태로 저장 |
| 대상 Snapshot | 작업 단계/작업 후 결과가 같은 구조로 저장 |
| 원본 근거 | 비교 finding에서 관련 장비/명령 결과를 추적 가능 |
| 손상/누락 | 읽을 수 없는 결과를 정상 상태로 임의 보정하지 않음 |

### 비교

| 항목 | 합격 기준 |
|---|---|
| 동일 항목 연결 | 장비명 + command ID 기준으로 비교 |
| 변동성 억제 | clock/uptime/날짜 등 무의미한 변화 감소 |
| Interface | Down 변화가 별도 finding으로 표시 |
| LACP | Selected 멤버 감소를 별도 finding으로 표시 |
| OSPF | Full 이탈 등 Neighbor 위험 상태 표시 |
| VRRP | 역할 변화/Down 상태 구분 |
| Hardware | Power/Fan/Alarm/모듈 비정상 상태 표시 |
| CPU | warning/critical 임계값 적용 |
| Memory | FreeRatio warning/critical 임계값 적용 |
| Log | 신규 긴급/주의 키워드를 다른 상태와 함께 확인 가능 |

### Expected Change

| 항목 | 합격 기준 |
|---|---|
| 작업 단계 | stage slug 기반 규칙 적용 가능 |
| 장비 | 특정 장비에만 규칙 제한 가능 |
| 명령 | 특정 command ID에만 규칙 제한 가능 |
| 근거 보존 | expected로 분류되어도 finding과 evidence가 사라지지 않음 |
| 비예상 변화 | 규칙에 맞지 않는 변화는 일반 finding으로 유지 |

### 보고서/진단

| 항목 | 합격 기준 |
|---|---|
| 결과 분류 | 긴급/주의/정보/변경없음 구분 |
| 영향 설명 | finding별 impact reason 제공 |
| 1차 조치 | action hint 제공 |
| HTML | 비교 결과를 브라우저에서 확인 가능 |
| 안전 진단 | 원본 장비 로그 없이 단계/오류 코드 중심 공유 가능 |
| 마스킹 | IP/Hostname/계정/secret 등 공개 금지 정보 비식별화 |

## 기본 자동 검증

```powershell
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
python webapp_launcher.py --smoke
```

진단 경계:

```powershell
python app.py --diagnose --self-check
```

PR Validation에서는 hash lock으로 의존성을 설치한 Windows runner에서 회귀·smoke·합성 진단·Ruff·Bandit·의존성 감사를 실행합니다. 이어 통합 ZIP과 CycloneDX 1.6 SBOM을 만들고 `tools/verify_release_assets.py`로 ZIP 구조, SHA-256, manifest source commit, SBOM 고정 버전과 GitHub attestation에 필요한 UUID `serialNumber`를 다시 확인합니다.

공개 근거는 자동/Mock/Windows CI 범위로 제한합니다. 기존 화면 이미지는 합성 샘플을 사용했으며 v0.9.0의 새 보안 경계 화면을 별도 브라우저 캡처로 재검증한 근거는 아닙니다.

## 운영 환경 검증 체크리스트

실제 장비에서 검증할 때는 조직 정책과 승인 범위 안에서 다음을 확인합니다.

| 항목 | 확인 내용 |
|---|---|
| 접속 | 허가된 계정으로 대상 장비 상태 조회 성공 |
| 장비 영향 | 설정 모드 진입 및 구성 변경 없음 |
| 출력 완전성 | 페이징으로 인해 중간 출력 누락 없음 |
| Interface | 수동 CLI 결과와 Snapshot 상태 일치 |
| LACP | 집계/멤버 상태와 비교 finding 일치 |
| OSPF | Neighbor 상태와 비교 finding 일치 |
| VRRP | Master/Backup/VIP 관련 상태와 finding 일치 |
| Hardware | PSU/Fan/Alarm 상태와 finding 일치 |
| CPU/Memory | 수동 확인 수치와 보고서 값 일치 |
| 작업 전/후 | 실제 변경 전후 차이를 기대한 수준으로 표시 |
| Expected Change | 계획된 OFF/복구 단계와 규칙 표시가 일치 |
| 접속 실패 | 한 장비 접속 실패가 여러 명령 장애처럼 증폭되지 않음 |
| 결과 파일 | Snapshot/HTML 결과 정상 열림 |
| 반복 실행 | 이전 임시 상태가 다음 작업을 오염시키지 않음 |

## 공개 가능한 운영 검증 요약 형식

실제 장비 검증이 완료되어도 공개 저장소에는 다음 수준의 요약만 기록합니다.

```text
운영 환경 검증
- 대상: HPE/Aruba 계열 백본 장비
- 읽기 전용 상태 수집: 확인
- Interface/LACP/OSPF/VRRP 비교: 확인
- CPU/Memory/Hardware 상태 확인: 확인
- 작업 전/후 Snapshot 비교: 확인
- 장비 설정 변경: 없음 확인
- 실제 장비명/IP/출력 원문: 비공개
```

## 검증 완료가 의미하지 않는 것

현재 검증이 다음을 자동으로 보장하지는 않습니다.

- 모든 HPE/Aruba/Comware 계열 버전의 출력 형식 호환성
- 모든 네트워크 장애 원인의 자동 진단
- 모든 사이트에 동일한 CPU/Memory 임계값의 적합성
- Expected Change 규칙에 등록된 변화의 실제 서비스 정상성
- 조직의 변경관리 승인이나 장애 종료 판단 대체

최종 운영 판단은 실제 서비스 상태, 변경 계획, 장비 CLI와 함께 수행해야 합니다.
