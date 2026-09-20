# 001 — 계획 1(백엔드 골격과 로그인) 검토에서 계획 2로 넘기는 항목

- 날짜: 2026-09-20
- 대상 브랜치: `feat/foundation-1-backend-auth` (c24fdbe..19c12e9, 커밋 20개, 테스트 83개, 구조 계약 4종 유지)
- 근거: 작업 단위 검토 11회, 브랜치 전체 최종 검토 1회, 수정 묶음 재검토 1회

계획 1은 최종 검토에서 "수정 후 머지" 판정을 받았고, 머지 전 수정 7건을 반영했다. 이 문서는 **의도적으로 미룬 것**을 적는다. 계획 2를 쓸 때 이 목록을 먼저 읽는다.

## 계획 2의 첫 작업으로 다룰 것

1. **실제 배선을 통과하는 통합 테스트.** 지금은 프로바이더 → `auth_wiring` → `get_db` 커밋 → Redis 구간을 `backend/scripts/check_auth_flow.sh` 수동 실행만 검증한다. `auth_main.app`과 `main.app`에 ASGITransport로 붙어 dev 로그인 → `/v1/me` → 갱신 → 재사용 401 → 로그아웃을 도는 `integration` 테스트를 둔다. 인증 프로세스를 테스트 컨테이너에서 import하려면 개인키 주입 방식을 먼저 정해야 한다. `UnsupportedProviderError` → 400, 갱신의 정지 403·무효 401 같은 HTTP 수준 경로도 여기서 함께 확인한다.
2. **시드와 테스트 픽스처의 충돌.** `backend/conftest.py`의 `db_session`은 `create_all`로 테이블을 만든다. 역할·권한은 Alembic 시드로 넣기로 했으므로 tenancy 통합 테스트 DB에는 시드가 없게 된다. 픽스처가 테스트 DB에 `alembic upgrade head`를 돌리게 바꾸는 쪽을 우선 검토한다. 그러면 수기 마이그레이션과 ORM의 불일치도 함께 잡힌다.
3. **스포크 간 조립 위치.** `get_me`는 `MembershipDirectoryPort` 구현이, `withdraw`는 `MembershipLifecyclePort` 구현이 필요하다. `auth/dependencies/*_provider.py`가 `tenancy.adapter…`를 import하면 다섯 번째 구조 계약(스포크 상호 독립)을 어긴다. 계약을 쓰기 전에 하나를 정한다: 조립을 진입점(`main.py`, `auth_main.py`)으로 올린다 / 허브에 레지스트리를 둔다 / `*.dependencies`를 계약의 예외로 둔다.
4. **ORM 등록 목록을 한 모듈로 모은다.** `alembic/env.py`와 `conftest.py`가 ORM 모듈을 각자 import한다.

## withdraw·계정 연결 작업에서 함께 다룰 것

5. **동시 재사용 시 "모든 세션 폐기"가 새로 발급되는 토큰을 놓치는 경합.** 같은 리프레시 토큰이 동시에 두 번 들어오면, USED 쪽의 `revoke_all`이 ACTIVE 쪽의 `save`보다 먼저 끝나 새 토큰이 살아남는다. 유저별 세대 번호(`revoke_all`이 세대를 올리고 `save`가 세대 일치를 확인)로 막는다. 포트 시그니처가 바뀌므로 같은 "모든 세션 폐기"를 쓰는 withdraw 전에 한 번에 설계한다. 이때 Lua 스크립트의 유저 집합 키를 `KEYS`로 옮긴다(Redis Cluster 대비).
6. **`IDENTITY_TOKEN_ENC_KEY`를 `.env.auth`로 옮긴다.** 복호화가 필요한 것은 인증 프로세스뿐이다. 읽기 전용 경로(`get_me`)의 리포지토리는 cipher 없이 조립한다.
7. **동시 가입 시 `IntegrityError` → 500.** `link_identity`의 409 처리와 같은 자리에서 다룬다(리포지토리에서 잡아 다시 조회).
8. **`SocialLoginInteractor`가 `is_deleted`를 보지 않는다.** withdraw가 익명화 뒤 신원 삭제 전에 실패하면 "로그인은 되는데 모든 요청이 401"인 상태가 생길 수 있다.
9. **Apple 리프레시 토큰 보완.** 지금은 가입 시점에만 저장한다. 첫 로그인에 인가 코드가 없었던 유저는 탈퇴 때 Apple 연결을 끊을 수 없다. 값이 비어 있으면 로그인 때 채운다.
10. **공용 `httpx.AsyncClient`를 lifespan에서 닫는다.** `revoke`로 HTTP 사용이 늘 때 옮긴다.

## 결정이 필요한 것 (설계 수준)

11. **재사용 감지의 유예.** 모바일에서 갱신 응답이 유실된 뒤 재시도하면 탈취로 판정되어 전 세션이 로그아웃된다. 직전 토큰을 수 초간 허용할지 정해서 기록한다.
12. **GoF 대응표의 "Factory Method" 표기.** `SocialProviderFactory`는 실제로는 제공자별 인스턴스 레지스트리이고 `build_social_provider_factory`는 단순 팩토리다. 표기를 "Factory"로 완화할지 정한다.

## 운영 전환 때 챙길 것

13. compose가 저장소 전체를 두 컨테이너에 마운트하므로 backend 컨테이너에서도 `.env.auth` 파일을 읽을 수 있다. 개인키 경계는 지금 "API 프로세스 경로가 `core.auth_config`를 import하지 않는다"는 규율로만 지켜진다. 배포 구성에서는 파일 수준으로 분리한다.
14. `/v1/auth/social`과 `/v1/auth/refresh`에 요청 제한이 없다.
15. `/docs`가 두 프로세스에 열려 있다.
16. `requirements.txt`가 하한(`>=`)뿐이고 잠금 파일이 없다. 이 브랜치가 FastAPI 0.137의 호환성 깨는 변경에 한 번 걸렸다. `pip freeze` 기반 constraints 파일을 둔다. `minio` 이미지에 태그를 단다.
17. `auth` 서비스가 마이그레이션을 기다리지 않아 첫 기동 직후 몇 초간 로그인이 500일 수 있다.

## 작은 것

18. JWKS 캐시: 모르는 `kid`가 와도 다시 가져오지 않는다(제공자가 키를 바꾸면 최대 1시간 실패). `raise_for_status`·네트워크 오류가 500으로 나간다. 캐시에 잠금이 없다.
19. 카카오 `id`·구글/Apple `sub`가 없을 때 `KeyError`가 500으로 나간다.
20. `RefreshTokenRedisStore`의 `status == "active"` 비교는 `decode_responses=True`인 클라이언트에서만 맞다.
21. `core/security.py`의 자체 토큰 검증에 `require_exp` 옵션이 없다.
22. `raise … from` 누락 2곳(`SocialProviderFactory.resolve`, `SocialLoginInteractor.login`).
23. 테스트 보강: `UserPgRepository.get`, 여러 신원일 때 `list_identities` 순서, `test_auth_myself_router`의 단언.

## 설계 문서 정정

24. 3.3절 키 목록에 `KAKAO_APP_ID`를 추가한다(구현이 옳다). `conftest.py`가 `load_auth_env()`를 부른다는 서술을 뺀다.
25. 3.1절의 `README.md`가 계획의 파일 지도에 없어 만들어지지 않았다.
26. `SocialProfile` docstring과 myself 문구의 "앱이 보낸 프로필은 믿지 않는다" — Apple의 `display_name`은 앱이 보낸 값이다. 문구를 정확하게 고친다.

## 실행 중 계획에서 벗어난 것 (모두 검토에서 타당 판정)

- MinIO 이미지: `minio/minio` → `quay.io/minio/minio` (Docker Hub에서 내려받을 수 없음)
- `RefreshTokenRedisStore.take`를 Lua 스크립트로 원자화 (계획 코드는 왕복 두 번이라 동시 재사용을 놓칠 수 있었음)
- `print_routes.collect_routes`가 `fastapi.routing.iter_route_contexts`를 사용, `fastapi>=0.137.2` (FastAPI 0.137의 공식 파괴적 변경에 대한 공식 대체 API)
- `get_db`를 `scope="function"`으로 정리하는 `DbSession` 도입 (응답을 보낸 뒤 커밋되던 결함, 실측 확인)
- `APP_ENV` 기본값 `"dev"` → `"prod"` (보안 게이트의 기본값은 닫힌 쪽)
- `IDENTITY_TOKEN_ENC_KEY` 필수화, `auth_main.py`가 기동 시 `core.auth_config` import
- 422·404·405 오류 본문도 `{code, message}`로 통일
- 표시 이름 50자 자르기, `python-jose>=3.4`
