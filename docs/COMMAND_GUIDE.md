# Backbone State Tracker 점검 명령어 가이드

문서 버전: v0.8.54
작성일: 2026-06-15
대상: 백본 3/4호기 상태 점검 및 휴전 작업 검증 담당자

## 1. 기본 원칙

- HPE/Comware 계열 백본 3/4호기에서 상태 확인을 위해 실행하는 읽기 전용 명령입니다.
- Cisco core 점검 명령이 아닙니다.
- 변경성 명령인 `system-view`, `save`, `reboot`, `reset`, `shutdown`, `undo`, `delete`는 포함하지 않습니다.
- 장비 접속 실패는 내부 항목 `device_connectivity`로 비교 결과에 포함됩니다.

## 2. 명령별 의미

| ID | 명령어 | 의미 | 핵심 확인 |
| --- | --- | --- | --- |
| `disable_paging` | `screen-length disable` | 페이지 넘김을 끄는 보조 명령 | 출력이 중간에 끊기지 않도록 합니다. |
| `system_clock` | `display clock` | 장비 시간 확인 | 시간 자체는 비교 노이즈로 제외됩니다. |
| `system_version` | `display version` | OS, 부팅 이미지, uptime 확인 | 예기치 않은 재부팅 또는 이미지 변화를 봅니다. |
| `device_status` | `display device` | 섀시/슬롯/모듈 상태 확인 | Fault, Abnormal, Offline, Missing 변화는 긴급입니다. |
| `power_status` | `display power` | 전원 상태 확인 | State가 Normal이 아니면 긴급입니다. |
| `fan_status` | `display fan` | 팬 상태 확인 | fan failure, stopped, abnormal 변화를 봅니다. |
| `environment_status` | `display environment` | 온도/센서 확인 | temperature alarm, over threshold 변화를 봅니다. |
| `alarm_status` | `display alarm` | 현재 알람 확인 | major alarm은 긴급, minor alarm은 주의입니다. |
| `interface_brief` | `display interface brief` | 인터페이스 up/down 요약 | 작업 계획과 무관한 Down은 긴급입니다. |
| `link_aggregation_summary` | `display link-aggregation summary` | LACP selected 수 확인 | selected 수 감소, unselected, not selected는 긴급입니다. |
| `link_aggregation_verbose` | `display link-aggregation verbose` | LACP 멤버 상세 | 특정 멤버만 빠지는지 확인합니다. |
| `vlan_summary` | `display vlan` | VLAN/포트 멤버십 확인 | VLAN 누락 또는 예상 밖 멤버십 변화를 봅니다. |
| `stp_brief` | `display stp brief` | STP 역할/상태 확인 | root, blocked, forwarding 변화를 확인합니다. |
| `ospf_peer` | `display ospf peer` | OSPF neighbor 확인 | Full 이탈, Init, ExStart, Loading은 긴급입니다. |
| `ospf_routes` | `display ip routing-table protocol ospf` | OSPF 경로 확인 | 주요 경로 삭제와 next-hop 변화를 봅니다. |
| `vrrp_status` | `show vrrp` | VRRP 상태 확인 | Master/Backup, priority, VIP, state 변화를 봅니다. Down/fail 계열은 긴급입니다. |
| `cpu_usage` | `display cpu-usage` | CPU 상태 확인 | 5초/1분/5분 값 중 70% 이상은 긴급, 50~69%는 주의, 모두 50% 미만은 정보입니다. |
| `memory_usage` | `display memory` | 메모리 상태 확인 | FreeRatio 30% 이하는 긴급, 31~40%는 주의, 40% 초과는 정보입니다. |
| `recent_log` | `display logbuffer` | 최근 시스템 로그 확인 | link down, neighbor down, alarm, error, failure 로그를 우선 확인합니다. |

## 3. 등급 기준

| 등급 | 기준 |
| --- | --- |
| 긴급 | 장비 접속 실패, 명령 실패, 인터페이스 Down, LACP selected 수 감소, OSPF Full 이탈, CPU 5초/1분/5분 70% 이상, memory FreeRatio 30% 이하, power State 비정상, major alarm, fault, abnormal, offline, missing |
| 주의 | CPU 5초/1분/5분 50~69%, memory FreeRatio 31~40%, minor alarm, warning, error, 라우팅/STP/로그/리소스 변화 중 긴급 키워드가 없는 변화 |
| 정보 | CPU 5초/1분/5분 모두 50% 미만, memory FreeRatio 40% 초과, 접속 복구 또는 긴급/주의로 단정하지 않는 일반 변경 |
| 변경없음 | 의미 있는 변경이 없는 항목 |

## 4. 작업 단계별 확인

| 시점 | 확인 내용 |
| --- | --- |
| 작업 전 | 백본3/4 접속 가능, OSPF Full, LACP selected 수, 주요 인터페이스 UP, CPU 5초/1분/5분 50% 미만, power State Normal, memory FreeRatio 40% 초과, 하드웨어/알람 정상 여부 |
| 백본3 OFF 중 | 백본3 접속 실패가 `device_connectivity`로 잡히는지, 백본4 경로가 예상대로 유지되는지 |
| 복구 후 | 백본3 접속 복구, OSPF Full, LACP selected 수 회복, CPU 5초/1분/5분 50% 미만, power State Normal, memory FreeRatio 40% 초과, 신규 알람 없음 |
