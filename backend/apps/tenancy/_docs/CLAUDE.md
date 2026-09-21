# tenancy — 매장, 역할·권한, 소속, 초대

소유 데이터: `shops`, `roles`, `permissions`, `role_permissions`, `shop_members`, `shop_invites`, Redis의 초대 코드 입력 횟수.

- 사장·직원은 계정 종류가 아니라 `shop_members`의 행이다. 같은 유저가 여러 매장에 속할 수 있다.
- `shop_members.user_id`는 auth의 유저 ID지만 외래 키를 걸지 않는다. 이름과 사진은 허브의 `UserDirectoryPort`로 받는다.
- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 컨텍스트가 없는 경로(소속 확인, 초대 수락, 매장 개설, 유저 기준 소속 목록)만 예외다.
- 역할과 권한은 마이그레이션 시드다. 코드에서 만들거나 고치지 않는다.
- 매장에는 사장이 한 명 이상 있어야 한다. 사장을 낮추거나 내보내기 전에 `count_owners`로 사장 행을 잠그고 센다.
- 초대 코드는 원문을 저장하지 않는다. 8자리(헷갈리는 글자 I·O·0·1 제외), SHA-256 해시 저장, 7일 만료, 1회 사용.
- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `resolve_shop_access`, `provision_shop`, `list_memberships`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
