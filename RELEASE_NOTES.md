# Release notes policy

현재 앱 버전: `v0.8.57`

이 파일은 GitHub Release notes를 수동으로 작성하는 파일이 아닙니다. 공개 GitHub Release body는 `.github/workflows/release.yml`이 `main` push 때 자동 생성합니다. 이 파일은 Release 전에 README, CHANGELOG, Release notes 형식이 현재 코드와 맞는지 확인하는 기준입니다.

## Release 전 문서 점검

1. `README.md`의 다운로드, GUI 실행, 웹앱 실행, 테스트, 빌드, 릴리스 파일 설명이 실제 파일과 맞는지 확인합니다.
2. 릴리스 파일명, 실행 파일명, 폴더 구조, 요구사항, 제한사항이 바뀌었으면 `README.md`를 수정합니다.
3. 릴리스에 보이는 변경이면 `CHANGELOG.md`에 사용자 관점 변경사항을 추가합니다.
4. GitHub Release body 형식이 바뀌면 `.github/workflows/release.yml`과 `tests/test_documentation.py`를 함께 수정합니다.
5. 릴리스 패키지에 새 파일을 포함하면 `tools/verify_release_package.py`, `tools/verify_release_package.ps1`, `tests/test_release_package_verifier.py`를 함께 수정합니다.
6. 최종 사용자용 ZIP에는 GUI와 웹앱만 포함하고 CLI 실행 파일과 CLI 실행 안내를 넣지 않습니다.
7. 실제 코드에 없는 기능은 문서에 쓰지 않습니다. 미구현 기능은 `미구현` 또는 `예정`으로 구분합니다.
8. 내부 IP, 실제 장비명, 계정, 비밀번호, 실제 로그, 고객 정보는 문서와 Release notes에 넣지 않습니다.

## 자동 GitHub Release notes 형식

자동 Release notes는 한국어로 작성하며 다음 순서를 유지합니다.

```md
vYYYY.MM.DD-HHMMSS 릴리스입니다.

변경내용:
- 이전 태그 이후 커밋 제목

검증:
- `python -m unittest discover -s tests` 통과
- `python app.py --smoke-check` 통과
- `python webapp_launcher.py --smoke` 통과
- Windows 통합 ZIP 빌드 통과
- Windows 통합 ZIP 구조 verifier 통과
- GUI 실행 파일 smoke 검증 통과
- 웹앱 실행 파일 smoke 검증 통과

빌드:
- `pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1 -SkipTests -ReleaseTag vYYYY.MM.DD-HHMMSS` 통과

첨부파일:
- 통합 Windows ZIP: `backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip`

실행 방법:
- GUI: ZIP 압축 해제 후 `gui\BackboneStateTracker.exe`를 더블클릭합니다.
- 웹앱: ZIP 압축 해제 후 `web\start_webapp.cmd`를 더블클릭합니다. 기본 주소는 `http://127.0.0.1:8765/`입니다.
- 웹앱 포트 변경: `web\start_webapp.cmd --port 8777`처럼 실행합니다.

중요 안내:
- GitHub가 자동으로 표시하는 `Source code (zip)` / `Source code (tar.gz)`는 소스 아카이브이며 일반 사용자 실행 파일이 아닙니다.
- 사용자 다운로드용 직접 업로드 asset은 위 통합 Windows ZIP 1개입니다.

배포 메타데이터:
- 브랜치명: `main`
- 기준 커밋 SHA: `...`
- 통합 ZIP 파일명: `...`
- SHA256 checksum: `...`
- 변경 커밋 목록: ...
```

## Git 커밋 파일과 Release asset 구분

Git에 커밋하는 파일:

- 소스 코드와 테스트
- `README.md`
- `RELEASE_NOTES.md`
- `CHANGELOG.md`
- `docs/`
- `config/commands.yaml`, `config/mock_profiles.yaml`, `config/analysis_rules.yaml`, `config/devices.example.yaml`
- `tools/` 릴리스 빌드/검증 스크립트

GitHub Release에 직접 업로드하는 파일:

- `backbone_state_tracker_<tag>_windows.zip`

GitHub Release에 직접 업로드하지 않는 파일:

- 별도 `.sha256` 파일
- CLI 실행 파일 또는 CLI 전용 안내 파일
- `outputs/`
- `dist/` 전체 폴더
- `build/`
- `.venv/`, `venv/`
- `config/devices.yaml`
- 실제 장비 로그, 내부망 정보, 고객 정보

GitHub가 자동으로 표시하는 `Source code (zip)` / `Source code (tar.gz)`는 제거할 수 없는 기본 항목입니다. Release notes에서 실행용 파일이 아니라고 안내합니다.

## Windows 통합 ZIP 빌드 주의

Windows 통합 ZIP은 GitHub Actions Windows runner 또는 Windows PC에서 검증합니다. macOS에서 소스 수정과 unittest는 할 수 있지만, macOS에서 Windows EXE가 직접 만들어진다고 문서화하지 않습니다.
