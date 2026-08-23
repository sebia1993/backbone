# 보안 정책

## 지원 버전

보안 수정은 최신 정식 릴리스인 `v0.9.0`에 우선 적용합니다. 이전 릴리스는 기존 증거 보존을 위해 유지하지만 별도 보안 수정은 보장하지 않습니다.

## 취약점 제보

실제 장비 주소, 계정, 암호, 장비 출력이나 내부 구성은 공개 Issue에 올리지 마세요. GitHub 저장소의 비공개 보안 제보 기능을 사용하고, 재현 절차에는 합성 주소와 마스킹된 자료만 포함하세요.

## 공개하지 않는 정보

Issue, Pull Request, commit, fixture, 문서와 Release asset에는 실제 장비 IP/Hostname, 계정·암호·SSH 개인키, token/API key/SNMP community, VLAN·라우팅·내부망 구성, 고객·사이트 식별정보, 원본 장비 출력·운영 로그, 로컬 `devices.yaml`과 실제 `known_hosts`를 포함하지 않습니다. 이미 노출됐다면 파일만 삭제하지 말고 자격 증명 폐기·교체, 공개 범위 확인, 이력과 Release 자산 정리, 재발 방지 검증을 함께 수행합니다.

## 실행 안전 경계

v0.9.0의 실제 장비 수집 경계는 다음 조건을 모두 만족하지 않으면 접속 전에 실패합니다.

- 장비 타입은 SSH 기반 `hp_comware`만 허용합니다. Telnet 또는 자동 프로토콜 하향 전환은 지원하지 않습니다.
- 모든 명령을 NFKC로 정규화한 뒤 길이, ASCII 문자, 제어 문자, 체이닝·파이프·리디렉션 문자와 전체 allowlist를 검사합니다.
- 허용 범위는 `display ...`, `show ...`, `screen-length disable`, 제한된 `terminal length N`뿐입니다.
- 전체 명령 검사가 끝나기 전에는 `ConnectHandler`를 호출하지 않으며, 실행에는 검사 후 생성한 정규 명령만 사용합니다.
- `config/known_hosts`를 Paramiko `HostKeys`로 사전 파싱하고 유효 키 엔트리를 1개 이상 요구합니다. 파일 없음·빈 파일·주석뿐인 파일·형식 오류는 모두 `ConnectHandler` 전에 차단합니다.
- 등록되지 않았거나 변경된 서버 키는 strict host-key 정책으로 연결을 차단합니다.
- 미등록·변경 서버 키는 일반 timeout과 구분해 `BST-SEC-002 SSH_HOST_KEY_REJECTED`로 기록하고 장비 명령을 실행하지 않습니다.
- SSH agent, 로컬 개인키 자동 탐색과 미등록 키 자동 추가를 사용하지 않습니다.
- `ssh-rsa`는 서버 호스트 키(`keys`)와 사용자 공개키 인증(`pubkeys`) 양쪽에서 비활성화합니다. 이를 위해 암호화 정책을 약화하지 않습니다.

## 호스트 키 등록

`ssh-keyscan` 결과는 신뢰 증거가 아니라 키를 가져오는 수단일 뿐입니다. 다음 절차를 모두 수행하세요.

1. 장비 콘솔, 관리 시스템 또는 보안 담당자에게 SHA256 fingerprint를 별도 채널로 받습니다.
2. 관리 PC에서 `ssh-keyscan -t ecdsa,ed25519 <host>`를 실행합니다. 비표준 포트는 `ssh-keyscan -p <port> -t ecdsa,ed25519 <host>`를 사용합니다.
3. `ssh-keygen -lf <scan-output>`의 SHA256 fingerprint가 1번 값과 같은지 직접 비교합니다.
4. 일치한 공개키 줄만 `config/known_hosts`에 저장합니다. 비표준 포트의 첫 필드는 `[host]:port`여야 합니다.
5. fingerprint가 바뀌면 기존 줄을 자동 교체하지 말고 변경 작업 또는 보안 사고 여부를 먼저 확인합니다.

`config/known_hosts`는 로컬 신뢰 자료이므로 Git과 릴리스 ZIP에서 제외됩니다. Windows ZIP 사용자는 압축 해제 후 `gui\config\known_hosts`를 직접 준비해야 합니다.

## CVE-2026-44405 임시 예외

2026-08-24 기준 Netmiko 4.7은 Paramiko `<5`를 요구합니다. Paramiko 4.0.0은 [CVE-2026-44405](https://nvd.nist.gov/vuln/detail/CVE-2026-44405)의 영향 범위에 있고, 수정 커밋 `a448945`를 포함한 호환 가능한 4.x 배포판은 아직 없습니다. 따라서 v0.9.0은 Paramiko `>=4,<5`를 일시 유지합니다.

보완 통제는 다음과 같습니다.

- 실제 SSH 연결마다 `disabled_algorithms={"keys": ["ssh-rsa"], "pubkeys": ["ssh-rsa"]}`를 강제합니다.
- `ssh_strict=True`와 전용 `known_hosts`를 함께 사용해 미등록·변경 호스트 키를 거부합니다.
- `ssh-rsa`만 제공하는 장비에는 연결 실패를 유지하며 자동으로 약한 알고리즘이나 Telnet을 사용하지 않습니다.
- 애플리케이션은 Paramiko의 RSA 서명 API를 직접 호출하지 않습니다.
- 회귀 테스트는 보완 통제 인자와 fail-closed 순서를 확인하고, Mock SSH도 ECDSA 키와 `RejectPolicy`로 실제 키 검증을 수행합니다.

잔여 위험은 Paramiko 4.0.0 코드가 의존성 그래프에 남는다는 점입니다. 이 예외의 담당자는 저장소 관리자이며 재검토 기한은 **2026-09-30**입니다. 그 전에 Netmiko가 수정된 Paramiko 버전을 지원하면 즉시 잠금 파일을 갱신하고 전체 Windows 검증을 수행합니다. 기한까지 호환 버전이 없으면 근거와 보완 통제를 다시 검토해 예외를 갱신하지 않는 한 다음 릴리스를 차단합니다.

## 검증과 한계

- CI와 Mock 결과는 합성 데이터와 GitHub-hosted Windows runner의 증거입니다.
- 공개 저장소에는 실제 HPE Comware 장비나 운영망 검증 완료 주장을 포함하지 않습니다.
- 비교 결과는 운영자의 변경 검증을 보조하며 변경 승인, 서비스 정상성 또는 장애 원인을 자동 확정하지 않습니다.
