# Backbone State Tracker 초급 개발자 가이드

버전: v0.3.0  
대상: Python 초급 개발자 또는 내부 유지보수 담당자

## 1. 프로젝트 구조

```text
backbone_state_tracker\
  app.py
  requirements.txt
  config\
    commands.yaml
    devices.example.yaml
  core\
    collector.py
    config.py
    diff_engine.py
    gui.py
    models.py
    paths.py
    reporter.py
    snapshot.py
    version.py
  docs\
  tests\
  tools\
```

## 2. 핵심 모듈

| 파일 | 역할 |
| --- | --- |
| `app.py` | GUI 실행 진입점 |
| `core/gui.py` | Tkinter 기반 화면과 버튼 동작 |
| `core/collector.py` | Netmiko SSH 접속 및 명령 실행 |
| `core/paths.py` | 소스 실행과 EXE 실행의 경로 기준 분리 |
| `core/snapshot.py` | 스냅샷 폴더와 원본 출력 저장 |
| `core/diff_engine.py` | 기준/대상 스냅샷 비교 |
| `core/reporter.py` | HTML, XLSX, JSON 리포트 생성 |
| `core/version.py` | 프로그램 이름, 버전, 릴리즈 날짜 |

## 3. 개발 환경 준비

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
python -m pip install -r requirements.txt
```

테스트를 루트 폴더에서 실행할 경우:

```powershell
cd "D:\Codex Project\Network"
python -m unittest discover -s backbone_state_tracker\tests
```

프로젝트 폴더 안에서 실행할 경우:

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
$env:PYTHONPATH = (Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
```

## 4. 점검 명령 추가 방법

명령은 `config/commands.yaml`에 추가합니다.

```yaml
- id: ospf_peer
  command: display ospf peer
  description: OSPF neighbor state. Full state should remain stable.
  category: routing
  allow_failure: true
  timeout: 45
```

필드 설명:

| 필드 | 설명 |
| --- | --- |
| `id` | 명령 결과 파일명과 비교 기준으로 쓰는 고유 ID |
| `command` | 장비에서 실행할 읽기 전용 명령 |
| `description` | 사용자에게 보여줄 설명 |
| `category` | 비교 등급 분류에 사용하는 범주 |
| `allow_failure` | 장비에서 지원하지 않아도 전체 수집을 계속할지 여부 |
| `timeout` | 명령별 대기 시간 |

## 5. 비교 등급 조정

비교 기준은 `core/diff_engine.py`에 있습니다.

- `VOLATILE_PATTERNS`: 시간, uptime 등 비교에서 제외할 줄
- `CRITICAL_PATTERNS`: Critical로 볼 키워드
- `WARNING_PATTERNS`: Warning으로 볼 키워드
- `classify_change()`: 명령 범주와 변경 내용을 바탕으로 등급 결정

변경 후에는 반드시 테스트를 추가하거나 기존 테스트를 실행합니다.

## 6. 버전 올리는 방법

1. `core/version.py`에서 `APP_VERSION`을 변경합니다.
2. `CHANGELOG.md`에 변경 내역을 추가합니다.
3. README와 가이드 문서의 버전 표기를 맞춥니다.
4. 테스트를 실행합니다.
5. Git 커밋과 태그를 남깁니다.

```powershell
git add .
git commit -m "Release v0.3.0"
git tag v0.3.0
```

## 7. ZIP 생성

소스 ZIP:

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

Windows 실행파일 ZIP:

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

생성 위치:

```text
dist\backbone_state_tracker_v0.3.0_YYYYMMDD_source.zip
dist\backbone_state_tracker_v0.3.0_YYYYMMDD_windows_exe.zip
```

ZIP 제외 대상:

- `.git`
- `outputs`
- `dist`
- `__pycache__`
- `.venv`
- `config/devices.yaml`

## 8. Git 운영 방식

권장 흐름:

```powershell
git checkout main
git checkout -b feature/my-change
# 코드 수정
python -m unittest discover -s tests
git add .
git commit -m "Describe my change"
git checkout main
git merge --no-ff feature/my-change
```

기능 단위로 브랜치를 나누면 어떤 변경이 언제 들어갔는지 추적하기 쉽습니다.

## 9. 주의사항

- 장비 설정 변경 명령을 추가하지 않습니다.
- 계정/암호를 코드, 문서, 테스트, 로그에 남기지 않습니다.
- 실제 장비 출력이 포함된 `outputs/` 폴더는 배포 ZIP에 포함하지 않습니다.
- HTML/JSON/XLSX 리포트에는 내부 네트워크 정보가 포함될 수 있으므로 공유 범위를 제한합니다.

