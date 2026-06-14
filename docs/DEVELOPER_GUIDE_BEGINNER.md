# Backbone State Tracker 초급 개발자 가이드

문서 버전: v0.8.42
작성일: 2026-06-14
대상: Python과 Windows 배포를 처음 유지보수하는 개발자

## 1. 프로젝트 목적

백본 3/4호기의 작업 전후 상태를 읽기 전용 명령으로 수집하고, 스냅샷 간 변경점을 GUI와 HTML/XLSX/JSON 리포트로 확인하는 Windows 운영 도구입니다.

## 2. 주요 파일

- `app.py`: 프로그램 시작점과 smoke-check 진입점입니다.
- `core/gui.py`: Tkinter GUI, 화면 전환, 수집/비교 버튼 동작을 관리합니다.
- `core/collector.py`: Netmiko 기반 SSH 읽기 전용 명령 수집입니다.
- `core/connectivity.py`: 장비 접속 가능/불가능 결과를 `device_connectivity`로 생성합니다.
- `config/commands.yaml`: 수집 대상 읽기 전용 명령을 관리하며, v0.8.35부터 `vrrp_status` / `show vrrp`가 포함됩니다.
- `core/diff_engine.py`: 스냅샷 비교, 변경 라인 추출, 긴급/주의/정보/변경없음 분류를 처리합니다.
- `core/reporter.py`: HTML, XLSX, JSON 리포트 생성입니다.
- `core/report_bundle.py`: 공유 ZIP 생성과 `docs/images` 포함 처리를 담당합니다.
- `core/workflow.py`: 기준 스냅샷, 사용자 지정 단계명, `점검시간` 기본명 규칙을 관리합니다.
- `core/preflight.py`: 장비/명령 설정의 로컬 검증입니다.
- `core/mock_validation.py`: 실제 장비 없이 샘플 스냅샷과 리포트를 생성합니다.
- `docs/images/`: 사용자 가이드에 포함되는 실제 앱 화면 캡처입니다.
- `tools/build_release.ps1`: 소스 ZIP 생성입니다.
- `tools/build_windows_exe.ps1`: Windows EXE ZIP 생성입니다.
- `tools/verify_release_package.py`, `tools/verify_release_package.ps1`: ZIP 검증기입니다.

## 3. 개발 환경

```powershell
cd "<folder-that-contains-backbone_state_tracker>\backbone_state_tracker"
python -m pip install -r requirements.txt
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python app.py
```

## 4. 테스트

변경 후 최소 검증:

```powershell
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
```

GUI 변경이 있으면 실제 앱을 실행해 화면이 비어 있지 않은지, 메뉴 순서가 `장비 설정`, `비교 결과`, `작업 로그`인지, 장비 설정 화면 안에서 상태 수집이 가능한지 확인합니다.

## 5. 현재 UI 구조

- 첫 화면: `장비 설정`
- 좌측 메뉴: `장비 설정`, `비교 결과`, `작업 로그`
- `장비 설정`: 접속 계정, 대상 장비, 상태 수집, 점검 명령 세트
- `장비 설정` 페이지는 세로 스크롤 가능한 Canvas 안에 구성해 장비 행이 늘어도 하단 수집 컨트롤에 접근할 수 있게 합니다.
- `대상 장비`: 기본 2개 입력 행을 만들고, `장비 추가`로 필요한 만큼 행을 늘립니다.
- 장비 YAML을 불러올 때 3대 이상이면 행을 자동 확장하고, 더 짧은 목록을 불러오면 남는 행은 빈 기본값으로 초기화합니다.
- `device_summary_var`는 `사용 N대 / 입력 N대 / 행 N개` 형식으로 대상 장비 입력 상태를 표시합니다.
- `상태 수집`: 사용자는 단계명만 입력합니다. 비우면 `점검시간_YYYYMMDD_HHMM`으로 저장됩니다.
- 수집/비교/샘플 검증 중에는 `_track_busy_sensitive()`에 등록된 실행 버튼을 비활성화합니다. 실행 흐름에 영향을 주는 버튼을 새로 만들면 같은 목록에 등록합니다.
- 첫 수집: 내부적으로 기준 스냅샷으로 저장합니다.
- 이후 수집: 사용자 지정 단계로 저장하고 최신 기준 스냅샷과 자동 비교합니다.
- `비교 결과`: 등급 카드 클릭으로 필터링하고, 변경 상세 행에서 원본 파일 열기/복사를 제공합니다.
- HTML 리포트: 처음에는 등급 카드만 보이고, 사용자가 `긴급`/`주의`/`정보`/`변경없음` 중 하나를 선택해야 해당 상태의 바로가기 버튼, 요약 카드, 상세 블록이 표시됩니다. 숨김 상태는 `[hidden]` CSS와 `aria-hidden` 동기화로 보강합니다.
- `작업 로그`: 수집 시작, 설정 오류, 비교 완료, 리포트 위치를 보여줍니다.
- 샘플 검증 스냅샷은 `sample_` slug와 폴더명으로 구분하며, `find_latest_pre_work_snapshot()`의 실제 기준 후보에서 제외합니다.
- GUI 상단 요약과 HTML 리포트 상단 메타에는 샘플 스냅샷을 `샘플:` 접두어로 표시합니다.

## 6. 등급 분류 기준

`core/diff_engine.py`의 `classify_change()`가 분류합니다.

- `Critical`: 장비 접속 실패, 명령 실패, 인터페이스 Down, LACP selected 수 감소, OSPF Full 이탈, `cpu_usage` 5초/1분/5분 70% 이상, `memory_usage` FreeRatio 30% 이하, `power_status` State 비정상, major alarm, fault, abnormal, offline, missing.
- `Warning`: `cpu_usage` 5초/1분/5분 50~69%, `memory_usage` FreeRatio 31~40%, minor alarm, warning, error, 라우팅/STP/로그/리소스 변화.
- `Info`: `cpu_usage` 5초/1분/5분 모두 50% 미만, `memory_usage` FreeRatio 40% 초과, 접속 복구 또는 일반 출력 변화.
- `Unchanged`: 정규화 후 의미 있는 변화가 없는 항목.

건강 상태를 의미하는 `No alarm`, `No fault`, `Normal`, `None`은 알람 키워드 오탐을 줄이기 위해 분류용 haystack에서 제외합니다. 단, `cpu_usage`와 `memory_usage`는 출력 변경량이 아니라 비교 대상 스냅샷의 현재 임계치 기준만으로 `Critical`/`Warning`/`Info`를 정합니다. `power_status`의 비정상 State 판정은 별도 구조화 파서로 처리합니다.

## 7. 문서와 스크린샷

- 사용자 가이드는 `docs/USER_GUIDE.md`와 `docs/USER_GUIDE.html`을 함께 수정합니다.
- 화면 캡처는 `docs/images/settings-collection.png`, `docs/images/compare-results.png`, `docs/images/work-log.png`를 사용합니다.
- 새 문서 자산을 추가하면 `tools/verify_release_package.py`와 `tools/verify_release_package.ps1`의 필수 파일 목록도 갱신합니다.

## 8. 릴리스 절차

1. `core/version.py`의 `APP_VERSION`을 올립니다.
2. `CHANGELOG.md`와 `docs/VERSION_HISTORY.md/html`을 갱신합니다.
3. 사용자/명령어/개발자/체크리스트 문서를 MD와 HTML 모두 갱신합니다.
4. `python -m unittest discover -s tests`와 `python app.py --smoke-check`를 실행합니다.
5. GUI 변경이 있으면 실제 앱 화면을 캡처해 검증합니다.
6. `tools/build_release.ps1`과 `tools/build_windows_exe.ps1`로 ZIP을 생성합니다.
7. Python/PowerShell 검증기로 소스 ZIP과 EXE ZIP을 모두 검증합니다.
8. Git 커밋과 버전 태그를 남깁니다.

## 9. 보안 주의

- 암호, 토큰, 실제 장비 원본 출력, 고객 데이터는 Git과 배포 ZIP에 넣지 않습니다.
- `config/devices.yaml`, `outputs/`, `raw/`, `dist/`, `build/`는 릴리스 ZIP에 포함하지 않습니다.
- 실제 장비 변경 명령은 추가하지 않습니다.
