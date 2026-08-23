# Release 운영 기준

현재 앱 버전: `v0.9.0`

이 문서는 HPE Comware 변경 검증기의 공개 Release를 언제 만들고, 어떤 증거와 자산을 함께 제공할지 정의합니다.

## Release 원칙

공개 Release는 **문서 수정이나 내부 정리만으로 자동 생성하지 않습니다.** `main`의 수동 workflow가 전체 Windows 검증을 다시 통과한 뒤 annotated tag와 Release를 생성합니다.

다음과 같이 사용자 또는 운영 의미가 있는 변경이 충분히 검증된 경우에만 배포합니다.

- 상태 수집 명령·안전 경계·SSH 정책 변경
- Snapshot 구조나 비교 의미 변경
- Interface/LACP/OSPF/VRRP 판정 변경
- CPU/Memory/Hardware 임계값 또는 finding 변경
- `expected_changes` 판정 의미 변경
- GUI/웹앱의 주요 운영 흐름 변경
- Windows 통합 ZIP 구조나 런타임 의존성 변경
- 운영상 중요한 오류 또는 보안 수정

## v0.9.0 핵심 변경

- 모든 명령을 네트워크 연결 전에 중앙에서 정규화하고, 읽기 전용임을 증명하지 못하면 실패하도록 변경했습니다.
- `hp_comware` SSH만 허용하고, 유효한 승인 키가 있는 `known_hosts`를 필수화했습니다.
- strict host-key 검증과 `ssh-rsa` host key/public-key 인증 차단을 Netmiko 연결 경계에 적용했습니다.
- Netmiko 4.7.0, Paramiko 4.0.0과 전체 전이 의존성을 SHA-256 hash lock으로 고정했습니다.
- 모의 SSH 서버와 클라이언트도 ECDSA 키와 명시적 `RejectPolicy`를 사용하도록 바꿨습니다.
- Windows 회귀·정적·보안 검사, CycloneDX 1.6 SBOM, SHA-256, manifest source commit, ZIP build provenance와 ZIP 대상 SBOM attestation을 릴리스 게이트에 포함했습니다.

## 배포 산출물

정식 버전은 SemVer 이름을 사용하며 네 개의 독립 asset을 제공합니다.

```text
backbone_state_tracker_v0.9.0_windows.zip
backbone_state_tracker_v0.9.0_windows.zip.sha256.txt
backbone_state_tracker_v0.9.0_release_manifest.txt
backbone_state_tracker_v0.9.0_sbom.cdx.json
```

ZIP에는 GUI와 로컬 웹앱 실행 환경, 공유 가능한 설정 예시만 포함합니다. 실제 `devices.yaml`과 `known_hosts`는 포함하지 않습니다. GitHub가 자동 표시하는 `Source code (zip)`과 `Source code (tar.gz)`는 실행용 배포 파일이 아닙니다.

## Release 전 검증

Windows runner 또는 Windows 환경에서 검증합니다.

```powershell
python -m pip install --require-hashes -r requirements-windows.lock
python -m pip check
python -m unittest discover -s tests
python app.py --smoke-check
python webapp_launcher.py --smoke
python -m ruff check --select F app.py webapp_launcher.py core tests tools
python -m bandit -q -lll -r app.py webapp_launcher.py core -x tests
```

완성된 네 자산은 `tools/verify_release_assets.py`로 ZIP 구조, SHA-256, manifest source commit, SBOM 형식과 고정 버전을 함께 확인합니다.

## Release notes 구성

1. 이번 릴리즈
2. 운영 영향
3. 검증 결과와 기준 commit
4. 다운로드·SHA-256·attestation
5. 알려진 범위

Release notes와 asset에는 실제 장비 IP/Hostname, 계정·암호, VLAN/라우팅 구성, 원본 출력·로그, token, SNMP community, 로컬 `devices.yaml`과 `known_hosts`를 포함하지 않습니다.

## 현재 알려진 범위

- 자동·Mock·Windows CI 결과는 실제 HPE Comware 장비나 운영망 호환성을 증명하지 않습니다.
- `ssh-rsa`만 제공하는 레거시 장비는 보안 정책을 낮추지 않고 연결 실패합니다.
- Paramiko CVE-2026-44405는 호환 가능한 수정 릴리스가 없는 상태이므로 `ssh-rsa` 키·public-key 알고리즘 차단을 보완통제로 유지하고 2026-09-30까지 재검토합니다.
- CPU/Memory 기본 임계값은 운영 환경에 따라 조정이 필요할 수 있습니다.
- `expected_changes`는 계획된 변화의 맥락을 표시하지만 실제 서비스 정상성을 보장하지 않습니다.
- 비교 결과는 변경 검증을 보조하며 조직의 변경 완료 승인이나 장애 종료 판단을 대체하지 않습니다.
