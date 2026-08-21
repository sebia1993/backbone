# Release 운영 기준

이 문서는 백본 상태 추적기의 공개 Release를 언제 만들고, 무엇을 검증하며, Release notes에 어떤 정보를 먼저 보여줄지 정의합니다.

## Release 원칙

공개 Release는 **문서 수정이나 내부 정리만으로 자동 생성하지 않습니다.**

`.github/workflows/release.yml`을 `main`에서 수동 실행하며 다음과 같이 사용자 또는 운영 의미가 있는 변경이 충분히 검증된 경우에만 배포합니다.

- 상태 수집 명령 또는 수집 방식 변경
- Snapshot 구조나 비교 의미 변경
- Interface/LACP/OSPF/VRRP 판정 변경
- CPU/Memory/Hardware 임계값 또는 finding 변경
- `expected_changes` 판정 의미 변경
- GUI/웹앱의 주요 운영 흐름 변경
- Windows 통합 ZIP 구조 변경
- 운영상 중요한 오류 수정
- 호환성에 영향을 주는 의존성 변경

오탈자, README 정리, 내부 개발 문서, 주석 수정은 다음 기능 Release에 함께 포함합니다.

## 배포 산출물

일반 사용자가 직접 받는 Release asset은 Windows 통합 ZIP 하나입니다.

```text
backbone_state_tracker_<tag>_windows.zip
```

ZIP에는 GUI와 로컬 웹앱 실행 환경을 포함합니다.

GitHub가 자동 표시하는 `Source code (zip)`과 `Source code (tar.gz)`는 실행용 배포 파일이 아닙니다.

SHA-256은 Release notes 본문에 기록합니다.

## Release 전 검증

기본 검증:

```powershell
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
python webapp_launcher.py --smoke
```

Windows 통합 패키지:

```powershell
pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1 -SkipTests -ReleaseTag <tag>
```

최종 ZIP은 다음 검증기를 다시 통과해야 합니다.

```powershell
python .\tools\verify_release_package.py <ZIP경로> --type windows --require-manifest --expected-sha256 <SHA256>
```

## Release notes 구성

Release 첫 화면에서는 커밋 목록보다 **운영자가 업그레이드 필요성과 영향을 판단할 정보**를 먼저 보여줍니다.

권장 순서:

1. 이번 릴리즈
2. 운영 영향
3. 검증 결과
4. 다운로드와 SHA-256
5. 알려진 범위
6. 세부 커밋

## 운영 영향 작성 기준

다음 항목을 구분해 설명합니다.

- 장비 설정 변경 여부
- 수집 대상 명령 변화
- Snapshot/비교 결과 호환성 영향
- Finding severity 또는 임계값 변화
- `expected_changes` 의미 변화
- 사용자가 다시 확인해야 할 설정
- 배포 ZIP 구조 변화

단순 문서 변경이나 UI 문구 변경에 습관적으로 보안 항목을 붙이지 않습니다.

## 공개하지 않는 정보

Release notes와 asset에는 다음 정보를 포함하지 않습니다.

- 실제 백본 장비 IP / Hostname
- 계정과 비밀번호
- 내부 VLAN / 라우팅 / 네트워크 구성
- 실제 장비 원본 출력과 로그
- 고객/사이트/조직 식별 정보
- token, SNMP community 등 secret
- 로컬 `config/devices.yaml`

문서 예시는 문서용 IP와 가상 장비명을 사용합니다.

## Windows 통합 ZIP 구성

최종 사용자에게 필요한 핵심 경로는 다음과 같습니다.

```text
README_START_HERE_KO.txt
gui/
  BackboneStateTracker.exe
web/
  start_webapp.cmd
```

CLI 실행 파일과 CLI 전용 안내는 최종 사용자용 통합 ZIP에 포함하지 않습니다.

## 현재 알려진 범위

- 모든 HPE/Aruba 계열 OS 버전의 출력 형식을 자동 보장하지 않습니다.
- CPU/Memory 기본 임계값은 운영 환경에 따라 조정이 필요할 수 있습니다.
- `expected_changes`는 계획된 변화의 맥락을 표시하지만 실제 서비스 정상성을 보장하지 않습니다.
- Windows EXE는 Windows runner 또는 Windows 환경에서 검증합니다.
- 비교 결과는 변경 검증을 보조하며 조직의 변경 완료 승인이나 장애 종료 판단을 대체하지 않습니다.
