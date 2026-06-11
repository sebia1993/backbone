# Backbone State Tracker 버전별 변경내용

문서 버전: v0.2.1  
작성일: 2026-06-11  
대상: 운영자, 인수자, 초급 유지보수 담당자

## 1. 문서 목적

이 문서는 Backbone State Tracker가 버전별로 어떤 기능과 문서를 추가했는지
쉽게 확인하기 위한 릴리즈 노트입니다. `CHANGELOG.md`가 개발자용 변경 로그라면,
이 문서는 사내 반입/운영 인수 시 빠르게 읽을 수 있는 요약 문서입니다.

## 2. 최신 버전 요약

| 버전 | 날짜 | 핵심 변경 |
| --- | --- | --- |
| v0.2.1 | 2026-06-11 | 버전별 변경내용 문서 추가 |
| v0.2.0 | 2026-06-11 | Git 기록, ZIP 배포, 사용자/개발자 가이드 추가 |
| v0.1.0 | 2026-06-11 | 백본 상태 수집/비교 도구 최초 구현 |

## 3. v0.2.1 변경내용

### 추가

- `docs/VERSION_HISTORY.md` 추가
- `docs/VERSION_HISTORY.html` 추가
- README의 가이드 문서 목록에 버전별 변경내용 문서 링크 추가

### 변경

- 프로그램 버전 표기를 `v0.2.1`로 갱신
- `CHANGELOG.md`에 `v0.2.1` 항목 추가

### 운영 영향

- 기존 스냅샷 수집, 비교, 리포트 생성 기능에는 영향이 없습니다.
- ZIP 배포 파일명은 `backbone_state_tracker_v0.2.1_YYYYMMDD_source.zip` 형식으로 생성됩니다.
- 새 문서는 ZIP에 자동 포함됩니다.

## 4. v0.2.0 변경내용

### 추가

- 독립 로컬 Git 저장소 구성
- `v0.1.0`, `v0.2.0` 태그 기반 버전 기록
- `tools/build_release.ps1` 릴리즈 ZIP 생성 스크립트
- 사용자 가이드 `docs/USER_GUIDE.md`, `docs/USER_GUIDE.html`
- 초급 개발자 가이드 `docs/DEVELOPER_GUIDE_BEGINNER.md`, `docs/DEVELOPER_GUIDE_BEGINNER.html`
- 중앙 버전 파일 `core/version.py`
- 변경 이력 파일 `CHANGELOG.md`

### 변경

- GUI 제목에 프로그램 버전 표시
- 스냅샷 메타데이터에 프로그램 이름과 버전 저장
- 비교 리포트 HTML에 프로그램 버전 표시
- README에 ZIP 생성 방법과 가이드 문서 위치 추가

### 운영 영향

- 사내 반입용 소스 ZIP을 표준 방식으로 생성할 수 있습니다.
- ZIP에는 `.git`, `outputs`, `dist`, `config/devices.yaml`, 캐시 파일이 포함되지 않습니다.
- 실제 장비 접속 정보와 수집 결과물이 배포 파일에 섞일 가능성을 낮췄습니다.

## 5. v0.1.0 변경내용

### 추가

- 백본 3호기/4호기 대상 상태 수집 GUI
- Netmiko 기반 SSH 접속 및 읽기 전용 명령 실행
- `config/commands.yaml` 기반 점검 명령 관리
- 시점별 스냅샷 저장
- 장비별 원본 명령 출력 보관
- 기준/대상 스냅샷 비교
- Critical, Warning, Info, Unchanged 등급 분류
- HTML, XLSX, JSON 비교 리포트 생성
- 스냅샷 및 비교 엔진 기본 단위 테스트

### 운영 영향

- 작업 전, 백본 3호기 OFF 중, 복구 후 상태를 각각 수집해 비교할 수 있습니다.
- OSPF, LACP, interface, log 등 주요 상태 변화 추적이 가능합니다.
- 장비 설정 변경 명령은 포함하지 않았습니다.

## 6. 버전 확인 방법

GUI 상단 제목에서 현재 버전을 확인할 수 있습니다.

```text
Backbone State Tracker v0.2.1
```

소스 기준으로는 아래 파일을 확인합니다.

```text
core/version.py
```

## 7. 릴리즈 ZIP 생성 기준

릴리즈 ZIP은 아래 명령으로 생성합니다.

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

ZIP 파일명 예시:

```text
dist\backbone_state_tracker_v0.2.1_20260611_source.zip
```

## 8. 반입 전 확인사항

- ZIP 파일명에 의도한 버전이 포함되어 있는지 확인합니다.
- `docs/` 폴더에 사용자 가이드, 개발자 가이드, 버전별 변경내용 문서가 모두 있는지 확인합니다.
- `config/devices.yaml`과 `outputs/`가 ZIP에 포함되지 않았는지 확인합니다.
- 장비 IP, 계정, 원본 출력 등 내부 정보가 반입 파일에 섞이지 않았는지 확인합니다.

