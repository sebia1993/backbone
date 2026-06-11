# Backbone State Tracker 사용자 가이드

버전: v0.4.0  
대상: 백본 3호기 / 백본 4호기 상태 수집 및 비교 담당자

## 1. 목적

Backbone State Tracker는 백본 3/4호기에서 읽기 전용 점검 명령을 실행하고,
작업 전/중/후 스냅샷을 비교해 달라진 점을 추적하는 Windows용 GUI 도구입니다.

이 도구는 장비 설정을 변경하지 않습니다. `display` 계열 상태 확인 명령만 실행합니다.

## 2. 패키지 종류

| 패키지 | 실행파일 포함 | 용도 |
| --- | --- | --- |
| `source.zip` | 아니오 | Python이 설치된 PC에서 소스 기준 실행/수정 |
| `windows_exe.zip` | 예 | `BackboneStateTracker.exe`로 바로 실행 |

메일 시스템은 `.exe`, `.py`, `.ps1`이 들어 있는 ZIP을 차단할 수 있습니다.
메일 업로드가 막히면 사내 승인된 파일 반입/전송 절차를 사용해야 합니다.

## 3. 설치

1. ZIP 파일을 사내 PC의 원하는 위치에 압축 해제합니다.
2. `windows_exe.zip`이면 `BackboneStateTracker.exe`를 실행합니다.
3. `source.zip`이면 PowerShell을 열고 프로젝트 폴더로 이동합니다.

```powershell
cd "D:\NetworkTools\backbone_state_tracker"
python -m pip install -r requirements.txt
python app.py
```

## 4. 실행

실행파일 패키지는 `BackboneStateTracker.exe`를 실행합니다.
소스 패키지는 `python app.py`로 실행합니다.

화면은 3단계 작업 흐름으로 구성됩니다.

| 단계 | 목적 |
| --- | --- |
| 1. 장비 및 접속 설정 | 접속 계정, 암호, 백본 3/4호기 정보를 입력 |
| 2. 작업 단계 선택 및 상태 수집 | 작업 전, 백본3 OFF 중, 복구 후 상태 수집 |
| 3. 자동 비교 및 결과 확인 | 작업 전 기준으로 자동 비교된 리포트 확인 |

1단계에서 다음 값을 입력합니다.

| 항목 | 설명 |
| --- | --- |
| Username | 백본 장비 SSH 접속 계정 |
| Password | 백본 장비 SSH 접속 암호. 파일에 저장되지 않습니다. |
| Timeout | 장비 접속 및 명령 대기 시간 |
| Device | 백본 3호기와 4호기 이름, IP, SSH 포트, Netmiko device type |

## 5. 장비 정보 저장

화면에서 장비 정보를 입력한 뒤 `Save Devices`를 누르면
`config/devices.yaml`에 저장됩니다.

주의: 이 파일에는 내부 IP나 호스트명이 들어갈 수 있으므로 ZIP 배포 파일에는 포함되지 않습니다.

## 6. 스냅샷 수집

1. 장비 정보와 계정 정보를 입력합니다.
2. 작업 단계를 선택합니다.
   - `작업 전`: 자동 비교 기준 스냅샷
   - `백본3 OFF 중`: 수집 후 최신 작업 전 스냅샷과 자동 비교
   - `복구 후`: 수집 후 최신 작업 전 스냅샷과 자동 비교
   - `사용자 지정`: 지정한 단계명으로 저장 후 최신 작업 전 스냅샷과 자동 비교
3. `상태 수집 시작`을 누릅니다.
4. 하단 Run log에서 진행 상황을 확인합니다.

스냅샷은 아래 경로에 저장됩니다.

```text
outputs\snapshots\YYYYMMDD_HHMMSS_스냅샷명\
```

각 스냅샷에는 장비별 원본 명령 출력과 `snapshot.json` 메타데이터가 저장됩니다.

## 7. 스냅샷 비교

`백본3 OFF 중`, `복구 후`, `사용자 지정` 단계는 수집 완료 후 자동으로 최신 `작업 전` 스냅샷과 비교합니다.

수동으로 다시 비교하려면:

1. `목록 새로고침`을 눌러 스냅샷 목록을 갱신합니다.
2. `기준 스냅샷(작업 전)`에 기준 스냅샷을 선택합니다.
3. `비교 스냅샷`에 비교 대상 스냅샷을 선택합니다.
4. `선택 항목 다시 비교`를 누릅니다.

비교 결과는 Target 스냅샷 아래에 생성됩니다.

```text
outputs\snapshots\<target>\comparisons\vs_<baseline>\
```

생성 파일:

| 파일 | 설명 |
| --- | --- |
| diff_report.html | 브라우저에서 보는 비교 리포트 |
| diff_summary.xlsx | 엑셀 요약 리포트 |
| diff_manifest.json | 자동화/추적용 원본 비교 데이터 |

## 8. 리포트 해석

| 등급 | 의미 | 예시 |
| --- | --- | --- |
| Critical | 서비스 영향 가능성이 큰 변경 | Interface down, OSPF neighbor down, LACP member unselected |
| Warning | 확인이 필요한 운영 상태 변경 | Route/log/resource 상태 변화 |
| Info | 참고용 출력 변화 | 단순 출력 차이 |
| Unchanged | 의미 있는 변경 없음 | 기준과 대상 출력 동일 |

## 9. 작업 시 권장 흐름

1. 작업 전: `pre` 스냅샷 수집
2. 백본 3호기 OFF 중: `bb3_off` 스냅샷 수집
3. 복구 후: `post_restore` 스냅샷 수집
4. 자동 생성된 비교 리포트 확인
5. 긴급/주의 항목을 먼저 확인

## 10. 보안 주의사항

- 암호는 프로그램 실행 중에만 사용하며 파일로 저장하지 않습니다.
- `config/devices.yaml`은 내부 IP/호스트명을 포함할 수 있으므로 외부 공유 전 확인해야 합니다.
- `outputs/`에는 장비 상태 출력이 포함되므로 외부 반출 대상에서 제외하는 것이 좋습니다.
- ZIP 릴리즈 스크립트는 `.git`, `outputs/`, `config/devices.yaml`을 자동 제외합니다.
- 실행파일 ZIP은 메일 보안 정책에서 차단될 수 있습니다.

## 11. 문제 해결

| 증상 | 확인 사항 |
| --- | --- |
| 접속 실패 | IP, SSH 포트, 계정, 방화벽, 장비 SSH 활성화 여부 확인 |
| 인증 실패 | 계정/암호 확인 |
| 명령 실패 | 장비 OS와 명령 지원 여부 확인 |
| HTML 리포트가 열리지 않음 | `Open Outputs`로 폴더를 열고 HTML 파일을 직접 실행 |
| XLSX 생성 실패 | `openpyxl` 설치 여부 확인 |

