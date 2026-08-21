# 변경 검증 로직

이 문서는 백본 상태 추적기가 작업 전·후 Snapshot을 비교할 때 어떤 변화를 중요하게 보는지 정리합니다.

## 기본 원칙

비교 엔진은 단순 문자열 차이만 표시하지 않습니다.

1. 작업 전·후 같은 장비와 같은 command ID를 연결합니다.
2. 시각·uptime 등 변동성이 높은 값을 정규화합니다.
3. 현재 상태가 임계조건을 위반하는지 별도로 확인합니다.
4. 위험 신호가 있으면 severity와 finding을 부여합니다.
5. 작업 단계에서 계획된 변화인지 `expected_changes`와 대조합니다.
6. 결과에는 영향 이유와 1차 확인 방향을 함께 제공합니다.

## 결과 분류

| 분류 | 의미 |
|---|---|
| 긴급 | 링크/라우팅/전원/장비 접속 등 즉시 확인 가치가 큰 변화 |
| 주의 | 운영 영향 가능성이 있어 추이·작업계획과 대조할 변화 |
| 정보 | 의미 있는 변화는 있으나 즉시 장애로 보기 어려운 변화 |
| 변경없음 | 정규화 이후 의미 있는 차이가 확인되지 않음 |

Severity는 운영자 판단을 보조하기 위한 우선순위이며 장애 원인을 자동 확정하는 값이 아닙니다.

## 장비 연결 상태

장비 자체에 연결하지 못한 경우 각 show 명령이 모두 실패한 것으로 나열하지 않습니다.

```text
장비 접속 실패
  ↓
device_connectivity finding 생성
  ↓
해당 장비의 하위 명령 누락 경고 억제
```

이렇게 해야 하나의 관리망/SSH 문제를 Interface, OSPF, LACP, VRRP 등 여러 독립 장애처럼 오인하지 않습니다.

접속이 복구되면 `connection_restored` finding을 만들 수 있으며, 복구 후에는 다시 OSPF/LACP/Interface/Power 상태를 확인하도록 안내합니다.

## Interface

대표 입력은 `display interface brief`입니다.

작업 계획에 없는 Interface Down은 다음 영향을 줄 수 있어 우선 확인 대상으로 분류합니다.

- 물리 링크 단절
- LACP 멤버 감소
- 이중화 경로 축소
- OSPF 인접 영향
- 상위 서비스 경로 변화

Down 자체만 보고 원인을 확정하지 않고 관련 LACP/OSPF/로그와 교차 확인하도록 합니다.

## LACP

`display link-aggregation summary`와 상세 결과를 비교합니다.

Selected 멤버 수가 줄어들면 실제 forwarding 가능한 멤버가 감소했을 수 있으므로 별도 finding으로 분리합니다.

확인 포인트:

- 제외된 멤버 포트
- 상대 장비 상태
- planned shutdown 여부
- 작업 전 Selected 수와 작업 후 Selected 수

## OSPF

`display ospf peer`의 Neighbor 상태를 확인합니다.

정상적으로 유지되어야 할 Neighbor가 `Full`에서 벗어나면 라우팅 경로 변동 또는 단절 가능성이 있으므로 우선 확인합니다.

다음과 같은 상태 키워드는 위험 신호로 취급될 수 있습니다.

- Init
- ExStart
- Exchange
- Loading

OSPF finding은 Interface 상태와 OSPF route 결과를 함께 보는 것을 전제로 합니다.

## VRRP

`show vrrp` 결과에서 Master/Backup 역할과 priority 변화를 확인합니다.

VRRP 역할 변화 자체가 항상 장애는 아닙니다. 계획된 절체일 수 있으므로 다음을 함께 확인합니다.

- 현재 Master가 의도한 장비인지
- Virtual IP가 정상 응답하는지
- Priority가 작업 계획과 맞는지
- 상대 장비 VRRP 상태
- 복구 후 원래 역할로 돌아와야 하는 작업인지

VRRP Down 상태는 가상 게이트웨이 기능에 직접 영향을 줄 수 있으므로 별도 위험 finding으로 분류합니다.

## 하드웨어 / 전원

다음 명령을 조합해 확인합니다.

- `display device`
- `display power`
- `display fan`
- `display environment`
- `display alarm`

모듈, Fan, PSU, Alarm 등에서 비정상 상태가 확인되면 하드웨어 finding을 생성합니다.

특히 Power 상태가 정상 범위를 벗어나면 장비 전원 이중화 저하 가능성이 있으므로 별도 항목으로 취급합니다.

## CPU

기본 기준은 `config/analysis_rules.yaml`에 정의되어 있습니다.

| CPU 사용률 | 기본 분류 |
|---:|---|
| 70% 이상 | 긴급 |
| 50~69% | 주의 |
| 50% 미만 | 정상 범위 정보 |

단일 시점 값만으로 원인을 확정하지 않고 작업 중 일시 피크인지, 지속되는지, 로그/트래픽 변화와 연관되는지 확인하도록 합니다.

## Memory

현재 기준은 FreeRatio입니다.

| FreeRatio | 기본 분류 |
|---:|---|
| 30% 이하 | 긴급 |
| 31~40% | 주의 |
| 40% 초과 | 정상 범위 정보 |

환경별 정상 범위가 다를 수 있으므로 임계값은 코드가 아니라 분석 규칙 파일에서 조정할 수 있도록 분리되어 있습니다.

## Log

`display logbuffer`의 신규 내용에서 위험 키워드를 확인합니다.

긴급 의심 예:

- down
- failure
- fault
- major alarm

주의 예:

- warning
- error
- minor alarm

로그 한 줄만으로 장애를 확정하지 않고 시각과 관련 Interface/OSPF/하드웨어 상태를 교차 확인합니다.

## 의미 없는 변화 억제

작업 전후 비교에서 다음 값은 실제 상태 변화가 없어도 달라질 수 있습니다.

- current time
- clock
- uptime
- boot time
- 날짜/시각 행

이러한 값은 정규화 대상으로 처리해 결과 화면이 실제 운영 변화에 집중하도록 합니다.

## Expected Change

작업 절차상 의도된 변화는 `config/analysis_rules.yaml`의 `expected_changes`로 정의할 수 있습니다.

규칙은 다음 맥락을 사용할 수 있습니다.

- stage slug
- device name
- command ID
- summary

예:

```text
백본3 OFF 단계
  + backbone3
  + device_connectivity
  + Target device connection failed
  → 계획된 OFF 단계의 접속 실패로 표시
```

중요한 원칙은 **Expected Change가 finding을 삭제하지 않는다는 것**입니다.

변화와 근거는 그대로 보존하고, 운영자에게 작업 계획과 일치하는 변화라는 추가 맥락만 제공합니다.

## 비교 결과 확인 순서

운영자는 다음 순서로 결과를 확인하는 것을 권장합니다.

1. 장비 접속 실패
2. Power/Hardware 긴급
3. Interface Down
4. LACP 멤버 감소
5. OSPF Neighbor 이탈
6. VRRP 역할/Down
7. CPU/Memory 긴급·주의
8. 신규 위험 로그
9. Expected Change 여부
10. 일반 출력 변화

최종 정상 판정은 도구의 severity만으로 결정하지 않고 작업 계획과 실제 서비스 상태를 함께 확인해야 합니다.
