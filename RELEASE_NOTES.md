# Release notes policy

현재 앱 버전: `v0.8.57`

이 파일은 GitHub Release notes를 수동으로 작성하는 파일이 아닙니다. 공개 GitHub Release body는 `.github/workflows/release.yml`이 `main` push 때 자동 생성합니다. 이 파일은 Release 전에 README, CHANGELOG, Release notes 형식이 현재 코드와 맞는지 확인하는 기준입니다.

## Release 전 문서 점검

1. `README.md`의 설치, 실행, 테스트, 빌드, 사용 방법이 실제 파일과 맞는지 확인합니다.
2. 릴리스 파일명, 실행 파일명, 폴더 구조, 요구사항, 제한사항이 바뀌었으면 `README.md`를 수정합니다.
3. 릴리스에 보이는 변경이면 `CHANGELOG.md`에 사용자 관점 변경사항을 추가합니다.
4. GitHub Release body 형식이 바뀌면 `.github/workflows/release.yml`과 `tests/test_documentation.py`를 함께 수정합니다.
5. 릴리스 패키지에 새 파일을 포함하면 `tools/verify_release_package.py`, `tools/verify_release_package.ps1`, `tests/test_release_package_verifier.py`를 함께 수정합니다.
6. 실제 코드에 없는 기능은 문서에 쓰지 않습니다. 미구현 기능은 `미구현` 또는 `예정`으로 구분합니다.
7. 내부 IP, 실제 장비명, 계정, 비밀번호, 실제 로그, 고객 정보는 문서와 Release notes에 넣지 않습니다.

## 자동 GitHub Release notes 형식

자동 Release notes는 다음 순서를 유지합니다.

```md
vYYYY.MM.DD-HHMMSS 릴리스입니다.

주요 변경사항:
- 이전 태그 이후 커밋 제목

검증:
- `python -m unittest discover -s tests` 통과
- `python app.py --smoke-check` 통과
- Windows EXE ZIP 빌드 통과
- Windows EXE release package verifier 통과

첨부파일:
- Windows EXE ZIP: `backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip`
- SHA256 sidecar: `backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip.sha256`

배포 메타데이터:
- 브랜치: `main`
- 기준 커밋 SHA: `...`
- 산출물 파일명: `...`
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

GitHub Release에 업로드하는 파일:

- `backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip`
- `backbone_state_tracker_v0.8.57_YYYYMMDD_windows_exe.zip.sha256`

Release asset으로 올리지 않는 파일:

- `outputs/`
- `dist/` 전체 폴더
- `build/`
- `.venv/`, `venv/`
- `config/devices.yaml`
- 실제 장비 로그, 내부망 정보, 고객 정보

## Windows EXE 빌드 주의

Windows EXE ZIP은 GitHub Actions Windows runner 또는 Windows PC에서 검증합니다. macOS에서 소스 수정과 unittest는 할 수 있지만, macOS에서 Windows EXE가 직접 만들어진다고 문서화하지 않습니다.
