# Backbone State Tracker 점검 명령어 가이드

문서 버전: v0.8.12
작성일: 2026-06-12
대상: 백본 3/4호기 상태 점검 및 휴전 작업 검증 담당자

## 1. 기본 원칙

- 이 명령 세트는 HPE/Comware 계열 백본 장비에서 상태 확인을 위해 실행하는 읽기 전용 명령입니다.
- Cisco core 점검용 명령이 아니며, 백본 3/4호기에서만 수집하는 흐름을 기준으로 합니다.
- `system-view`, `save`, `reboot`, `reset`, `shutdown`, `undo`, `delete` 같은 변경성 명령은 포함하지 않습니다.
- 작업 전, 백본3 OFF 중, 복구 후 스냅샷의 같은 명령 결과를 비교해 달라진 줄을 추적합니다.
- 장비 접속 실패는 별도 내부 항목인 `device_connectivity`로 비교 결과에 포함됩니다.

## 2. 세션 준비 명령

| ID | 명령어 | 의미 | 확인 포인트 |
| --- | --- | --- | --- |
| `disable_paging` | `screen-length disable` | 터미널 페이지 넘김을 끄고 명령 출력이 중간에 끊기지 않게 합니다. | 수집 보조 명령입니다. 실패해도 장비 상태 변화로 보지 않습니다. |

## 3. 기본 상태

| ID | 명령어 | 의미 | 정상 기준 | 추적 포인트 |
| --- | --- | --- | --- | --- |
| `system_clock` | `display clock` | 장비 시간 확인입니다. | 작업 시간대와 큰 차이가 없어야 합니다. | 시간 자체는 비교 노이즈가 크므로 변경 판단에서 제외됩니다. |
| `system_version` | `display version` | OS 버전, 부팅 이미지, 장비 uptime 확인입니다. | 작업 중 재부팅이 없으면 버전과 uptime 흐름이 자연스럽게 유지됩니다. | uptime 초기화, boot image 변경, 예기치 않은 reload 흔적을 봅니다. |

## 4. 하드웨어 상태

| ID | 명령어 | 의미 | 정상 기준 | 추적 포인트 |
| --- | --- | --- | --- | --- |
| `device_status` | `display device` | 섀시, 슬롯, 모듈 상태 확인입니다. | 주요 슬롯과 모듈이 Normal/Present 계열로 유지됩니다. | Fault, Abnormal, Offline, Missing, Down 계열 문자열이 새로 생기면 긴급 확인 대상입니다. |
| `power_status` | `display power` | 전원 공급 장치 상태 확인입니다. | 전원 모듈이 Normal 또는 안정 상태로 표시됩니다. | 전원 모듈 failure, absent, abnormal 변화가 있는지 봅니다. |
| `fan_status` | `display fan` | 팬 상태 확인입니다. | 팬이 Normal 또는 안정 상태로 표시됩니다. | fan failure, stopped, abnormal 변화가 있으면 온도/하드웨어 리스크가 있습니다. |
| `environment_status` | `display environment` | 온도와 환경 센서 상태 확인입니다. | 온도와 센서 상태가 정상 범위로 유지됩니다. | temperature alarm, over threshold, abnormal 문구를 봅니다. |
| `alarm_status` | `display alarm` | 현재 장비 알람 확인입니다. | 신규 major/minor alarm이 없어야 합니다. | 새 alarm, cleared되지 않은 major/minor 알람을 추적합니다. |

## 5. 인터페이스와 이중화 링크

| ID | 명령어 | 의미 | 정상 기준 | 추적 포인트 |
| --- | --- | --- | --- | --- |
| `interface_brief` | `display interface brief` | 인터페이스 up/down 요약입니다. | 백본4 ON 상태에서 서비스 경로 인터페이스가 예상 상태로 유지됩니다. | OFF 계획과 무관한 인터페이스 Down, admin down, error 상태를 확인합니다. |
| `link_aggregation_summary` | `display link-aggregation summary` | LACP/Link Aggregation 요약과 selected 멤버 수 확인입니다. | 집계 그룹과 selected 포트 수가 작업 시나리오에 맞게 유지됩니다. | selected 수 감소, unselected, not selected, partner 불일치를 봅니다. |
| `link_aggregation_verbose` | `display link-aggregation verbose` | 집계 링크의 멤버별 상세 상태 확인입니다. | 멤버 포트 상태와 peer 동기화 상태가 일관됩니다. | 특정 멤버만 unselected, partner mismatch, aggregation state 변화가 있는지 봅니다. |

## 6. 스위칭 상태

| ID | 명령어 | 의미 | 정상 기준 | 추적 포인트 |
| --- | --- | --- | --- | --- |
| `vlan_summary` | `display vlan` | VLAN 존재와 포트 멤버십 요약입니다. | 작업 전후 VLAN 목록과 주요 포트 멤버십이 의도대로 유지됩니다. | VLAN 누락, 포트 멤버십 변화, 예상 밖 tagged/untagged 변경을 봅니다. |
| `stp_brief` | `display stp brief` | STP 포트 역할과 상태 요약입니다. | 의도한 경로 전환 외 Root/Designated/Blocked 상태가 안정적으로 유지됩니다. | root 변경, blocked/forwarding 전환, topology change 증가를 확인합니다. |

## 7. 라우팅 상태

| ID | 명령어 | 의미 | 정상 기준 | 추적 포인트 |
| --- | --- | --- | --- | --- |
| `ospf_peer` | `display ospf peer` | OSPF neighbor 상태 확인입니다. | 정상 neighbor는 Full 상태로 유지됩니다. | Down, Init, ExStart, Exchange, Loading 상태가 새로 보이면 긴급 확인 대상입니다. |
| `ospf_routes` | `display ip routing-table protocol ospf` | OSPF 학습 경로와 next-hop 확인입니다. | 주요 OSPF 경로와 next-hop이 작업 시나리오에 맞게 유지됩니다. | 주요 경로 삭제, next-hop 변화, 우회 경로 미학습을 확인합니다. |

## 8. 리소스와 로그

| ID | 명령어 | 의미 | 정상 기준 | 추적 포인트 |
| --- | --- | --- | --- | --- |
| `cpu_usage` | `display cpu-usage` | CPU 사용률 확인입니다. | 작업 중 일시 상승은 가능하지만 지속 고부하는 없어야 합니다. | 높은 CPU가 지속되거나 프로세스 사용률이 급변하면 원인 추적이 필요합니다. |
| `memory_usage` | `display memory` | 메모리 사용률 확인입니다. | 사용률이 급격히 증가하지 않아야 합니다. | 여유 메모리 급감, abnormal, allocation failure 로그와 함께 봅니다. |
| `recent_log` | `display logbuffer` | 최근 시스템 로그 확인입니다. | 작업 범위 안의 링크/이웃 변화 외 신규 장애 로그가 없어야 합니다. | link down, OSPF neighbor down, power/fan/module alarm, error/failure 로그를 우선 확인합니다. |

## 9. 비교 결과 해석

- `긴급`: 인터페이스 Down, OSPF Full 이탈, 하드웨어 fault, 장비 접속 실패처럼 즉시 확인이 필요한 변화입니다.
- `주의`: 라우팅, STP, 로그, 리소스 상태가 바뀌었지만 긴급 키워드로 분류되지 않은 변화입니다.
- `정보`: 접속 복구나 일반 출력 변화처럼 기록은 필요하지만 즉시 장애로 단정하지 않는 변화입니다.
- `변경없음`: 의미 있는 변화가 감지되지 않은 항목입니다.

## 10. 작업 단계별 핵심 확인

| 단계 | 핵심 확인 |
| --- | --- |
| 작업 전 | 백본3/4 접속 가능, OSPF Full, LACP selected 수, 주요 인터페이스 UP, 하드웨어/알람 정상 여부를 기준으로 확보합니다. |
| 백본3 OFF 중 | 백본3 접속 실패가 `device_connectivity` 긴급 항목으로 잡히는지, 백본4에서 예상 경로만 유지되는지 확인합니다. |
| 복구 후 | 백본3 접속 복구, 백본3/4 OSPF Full, LACP selected 수 회복, 주요 인터페이스 UP, 신규 알람 없음 여부를 확인합니다. |
