# hub — 허브

스포크 사이의 계약(포트 ABC와 DTO)만 가진다. 구현은 스포크가 제공한다.

- 어떤 스포크도 import하지 않는다 (`.importlinter`의 허브 격리 계약).
- 포트는 실제로 쓰는 스포크가 생길 때 추가한다. 빈 껍데기 포트를 미리 만들지 않는다.
- 구현하는 스포크는 HTTP 표면이 없는 슬라이스로 만들고, 인터랙터가 포트 ABC를 직접 상속한다.
- 소비하는 스포크는 `dependencies/hub_ports.py`의 자리로 받는다. `main.py`가 구현을 꽂는다.
- 포트가 던지는 오류는 `app/errors.py`의 `HubPortError` 하위 타입뿐이다. 포트 docstring 이 어떤 타입을 언제 던지는지 적는다. 구현은 자기 도메인 오류를 밖으로 내보내지 않는다. 새 허브 오류는 `core/hub_errors.py`에 상태를 함께 적는다.

| 포트 | 구현 | 사용 |
|---|---|---|
| `ShopAccessPort.resolve(user_id, shop_id) → ShopContext` | tenancy `resolve_shop_access` | 매장 범위의 모든 스포크 (`core/shop_guard.py`) |
| `ShopProvisioningPort.create_shop(name, business_type) → ProvisionedShop` | tenancy `provision_shop` | platform_admin `create_shop` |
| `MembershipDirectoryPort.list_for_user(user_id) → list[MembershipSummary]` | tenancy `list_memberships` | auth `get_me` |
| `OperatorDirectoryPort.is_operator(user_id) → bool` | auth `check_operator` | platform_admin |
| `UserDirectoryPort.get_profiles(user_ids) → dict[int, UserProfile]` | auth `get_user_profiles` | tenancy `list_members` |
| `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |
| `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy `apply_withdrawal` | auth `withdraw` (인증 프로세스) |
| `CustomerDirectoryPort.lock_family · briefs · set_last_visit · set_pet_weight · find_draft_candidates(ctx, words) → list[DraftCandidate]` | customer `customer_directory` | visit (방문 쓰기의 가족 잠금, 이름 표시, 최근 방문순, 기록의 몸무게, 카톡 초안 후보) |
| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기·`latest_covers`) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세, 반려동물 프로필 사진) |
| `MediaLibraryPort.claim(ctx, ids) → {id: kind} · release · read_urls(ctx, ids) → {id: MediaUrls}` | media `media_library` | visit (기록의 사진·영상), customer (프로필 사진) |
