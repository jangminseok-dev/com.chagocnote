# auth — 신원과 토큰

소유 데이터: `users`, `social_identities`, `platform_operators`, Redis의 리프레시 토큰.

- User는 플랫폼에 하나만 있는 신원이다. 사장·직원·보호자는 계정 종류가 아니라 매장과의 관계이며 auth는 그 관계를 모른다.
- 토큰에는 유저 ID만 담는다. 역할과 권한을 넣지 않는다.
- 리프레시 토큰은 `{user_id}.{난수}` 모양이고 쓸 때마다 새 토큰으로 바꾼다. 이미 쓴 토큰이 다시 들어오면 그 유저의 세션을 모두 폐기한다.
- "모든 세션 폐기"는 유저의 세대(`auth:refresh:gen:{user_id}`)를 하나 올리는 것이다. 토큰 값에 발급 시점의 세대가 찍혀 있고, 꺼낼 때 현재 세대와 다르면 무효다. 갱신은 꺼낼 때 받은 세대로 새 토큰을 저장하므로, 그 사이 폐기가 끼어들면 새 토큰도 무효가 된다.
- 제공자별 검증은 `adapter/outbound/strategy/`에, 제공자를 고르는 코드는 `adapter/outbound/factory/`에 둔다.
- 개발용 제공자 `dev`는 `APP_ENV=dev`일 때만 등록된다. 이 동작은 테스트로 고정되어 있다.
- 토큰을 발급하는 코드는 `core/auth_config.py`(개인키)를 함수 안에서 import한다. 모듈 최상단에서 import하면 API 프로세스에서 모듈을 불러올 때 실패한다.
- 플랫폼 운영자는 유저에 붙는 전역 지정이다. `scripts/grant_operator.py <user_id>`로만 지정한다. 다른 스포크는 허브의 `OperatorDirectoryPort`로 묻는다.
- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `check_operator`, `get_user_profiles`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
