# auth — 신원과 토큰

소유 데이터: `users`, `social_identities`, `platform_operators`, Redis의 리프레시 토큰.

- User는 플랫폼에 하나만 있는 신원이다. 사장·직원·보호자는 계정 종류가 아니라 매장과의 관계이며 auth는 그 관계를 모른다.
- 토큰에는 유저 ID와 (소셜 로그인일 때) 로그인 시각(`auth_time`)만 담는다. 역할과 권한을 넣지 않는다.
- 리프레시 토큰은 `{user_id}.{난수}` 모양이고 쓸 때마다 새 토큰으로 바꾼다. 이미 쓴 토큰이 다시 들어오면 그 유저의 세션을 모두 폐기한다.
- "모든 세션 폐기"는 유저의 세대(`auth:refresh:gen:{user_id}`)를 하나 올리는 것이다. 토큰 값에 발급 시점의 세대가 찍혀 있고, 꺼낼 때 현재 세대와 다르면 무효다. 갱신은 꺼낼 때 받은 세대로 새 토큰을 저장하므로, 그 사이 폐기가 끼어들면 새 토큰도 무효가 된다.
- 제공자별 검증은 `adapter/outbound/strategy/`에, 제공자를 고르는 코드는 `adapter/outbound/factory/`에 둔다.
- 개발용 제공자 `dev`는 `APP_ENV=dev`일 때만 등록된다. 이 동작은 테스트로 고정되어 있다.
- 토큰을 발급하는 코드는 `core/auth_config.py`(개인키)를 함수 안에서 import한다. 모듈 최상단에서 import하면 API 프로세스에서 모듈을 불러올 때 실패한다.
- 플랫폼 운영자는 유저에 붙는 전역 지정이다. `scripts/grant_operator.py <user_id>`로만 지정한다. 다른 스포크는 허브의 `OperatorDirectoryPort`로 묻는다.
- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `check_operator`, `get_user_profiles`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
- 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있다. 제공자 토큰을 저장·복호화하는 경로는 `build_user_repository_with_cipher`로, 읽기만 하는 경로는 `build_user_repository`로 조립한다.
- 한 유저는 제공자마다 신원을 하나만 가진다. 계정을 바꾸는 유스케이스(`link_identity`·`unlink_identity`·`withdraw`)는 맨 앞에서 `UserRepository.lock`으로 유저 행을 잠그고 탈퇴 여부를 다시 본다.
- **현재 세대로 토큰을 발급하는 경로(`SessionIssuer.issue(..., generation=None)`)는 유저 행을 잠그고 다시 확인한다.** `social_login`·`unlink_identity`가 여기 해당한다. `social_login`은 기존 유저를 찾으면 그 행을 잠근 뒤 신원을 다시 조회한다 — 잠금이 없으면 해제·탈퇴와 겹친 로그인이 사라진 수단으로 30일 세션을 쥔다. 어긋나면 조회를 처음부터 한 번만 다시 하고(해제된 수단은 새 계정이 된다), 두 번째에도 어긋나면 거절한다. 로그인이 잠그는 것은 유저 행 하나뿐이고 그 뒤로는 아무것도 잠그지 않는다. `grant_operator`도 같은 이유로 `lock`으로 읽는다. `refresh_token`은 이 규칙 밖이다 — 유저를 `get`으로 읽지만, 꺼낼 때(`take`) 받은 세대로 새 토큰을 저장하므로 그 사이 끼어든 전체 폐기가 새 토큰도 함께 무효로 만든다.
- 잠금을 쥔 채 외부 HTTP를 부르지 않는다. 제공자 검증은 잠금 전에, 제공자 쪽 연결 끊기는 커밋 뒤 백그라운드 작업(`ProviderRevoker`)으로 한다. 끊지 못해도 탈퇴·해제는 끝난 것이며 로그만 남긴다. 구글은 서버가 끊지 않는다(앱이 `disconnect()`를 부른다).
- 로그인 수단을 해제하면 모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다.
- 민감한 계정 경로를 더할 때는 `dependencies/recent_login_guard.require_recent_login` 을 쓰고 `tests/route_inspection.py` 의 `_RECENT_LOGIN_PREFIXES` 에 경로를 적는다. 최근 로그인의 창(300초)과 시계 차 허용폭은 `domain/services/recent_login.py`가 정한다 — core 는 토큰 검증(`get_access_claims`)만 한다. `auth_time` 은 소셜 로그인만 새로 찍고(`fresh_login=True`), 갱신은 찍지 않으며, 해제는 요청 토큰의 값을 물려준다.
- 탈퇴의 DB 변경은 요청 하나의 트랜잭션이다. 소속 정리는 허브의 `MembershipLifecyclePort`(구현: tenancy)가 같은 세션에서 한다. 이 자리는 `auth_main.py`가 채운다.
