# Backbone State Tracker 버전별 변경내역

문서 버전: v0.8.18  
작성일: 2026-06-12  
대상: 운영자, 인수자, 초급 유지보수 담당자

## 1. 최신 버전

### v0.8.18 - 2026-06-12

- `상태 수집` 별도 메뉴와 작업 진행 마법사를 제거하고, 상태 수집 기능을 `장비 설정` 화면에 통합했습니다.
- 수집 단계 선택 UI를 제거하고 `수집 단계명(선택)` 단일 입력만 남겼습니다.
- 단계명을 입력하지 않으면 `점검시간_YYYYMMDD_HHMM` 형식으로 저장합니다.
- 첫 수집은 기준 스냅샷으로 저장하고, 이후 수집은 최신 기준 스냅샷과 자동 비교하도록 정리했습니다.
- GUI 비교 결과의 `긴급`, `주의`, `정보`, `변경없음` 요약 카드를 클릭하면 해당 등급만 필터링합니다.
- HTML 비교 리포트의 등급 카드도 필터로 동작합니다.
- HTML 리포트에서 `변경없음` 상세 블록은 기본 접힘 상태로 표시합니다.
- 장비 접속 실패는 비교 결과에서 `device_connectivity` 항목으로 계속 추적합니다.
- 긴급/주의 판단 기준을 재정의했습니다. LACP selected 수 감소, major alarm, 장비 접속 실패는 긴급이고, minor alarm과 warning/error 계열 운영 변화는 주의입니다.
- 사용자 가이드에 실제 앱 화면 캡처 3장을 추가했습니다.
- GUI 한글 렌더링 품질을 위해 기본 UI/로그 폰트를 `Malgun Gothic`으로 정리했습니다.
- 공유 ZIP과 릴리스 ZIP 검증 대상에 `docs/images/` 화면 캡처를 포함했습니다.

## 2. 이전 주요 변경

| 버전 | 날짜 | 주요 내용 |
| --- | --- | --- |
| v0.8.17 | 2026-06-12 | 앱 시작 화면을 `장비 설정`으로 재배치했습니다. |
| v0.8.16 | 2026-06-12 | HTML 요약 카드를 개선하고 비교 지표 영역을 축소했습니다. |
| v0.8.15 | 2026-06-12 | 대시보드 메뉴를 제거하고 작업 로그 자동 이동을 추가했습니다. |
| v0.8.14 | 2026-06-12 | checksum sidecar에 Date stamp 검증을 추가했습니다. |
| v0.8.13 | 2026-06-12 | release manifest 중복 Package 레코드 검증을 추가했습니다. |
| v0.8.12 | 2026-06-12 | ZIP 내부 중복 엔트리 검증을 추가했습니다. |
| v0.8.11 | 2026-06-12 | ZIP 경로 안전성 검증을 추가했습니다. |
| v0.8.10 | 2026-06-12 | manifest의 패키지 크기와 SHA256 레코드 검증을 강화했습니다. |
| v0.8.9 | 2026-06-12 | ZIP 파일명, sidecar, manifest의 버전/날짜 일치 검증을 추가했습니다. |
| v0.8.8 | 2026-06-12 | 릴리스 반입 체크리스트를 필수 문서로 추가했습니다. |
| v0.8.7 이하 | 2026-06-11 이전 | 스냅샷 비교, redaction, 공유 ZIP, 샘플 검증, GUI 상세 비교 기능을 단계적으로 추가했습니다. |

## 3. v0.8.18 산출물 이름

```text
dist\backbone_state_tracker_v0.8.18_20260612_source.zip
dist\backbone_state_tracker_v0.8.18_20260612_source.zip.sha256.txt
dist\backbone_state_tracker_v0.8.18_20260612_windows_exe.zip
dist\backbone_state_tracker_v0.8.18_20260612_windows_exe.zip.sha256.txt
dist\backbone_state_tracker_v0.8.18_20260612_release_manifest.txt
dist\backbone_state_tracker_v0.8.18_20260612_verify_release_package.ps1
```

## 4. 릴리스 검증 기준

- ZIP 파일명, checksum sidecar, release manifest의 버전과 날짜가 일치해야 합니다.
- ZIP 내부는 `backbone_state_tracker/` 루트 아래에 있어야 합니다.
- `config/devices.yaml`, `outputs/`, `raw/`, `dist/`, `build/`, `.git`, `__pycache__`는 포함하지 않습니다.
- MD/HTML 문서와 `docs/images/` 화면 캡처가 포함되어야 합니다.
- 소스 ZIP과 Windows EXE ZIP 모두 Python/PowerShell 검증기를 통과해야 합니다.
