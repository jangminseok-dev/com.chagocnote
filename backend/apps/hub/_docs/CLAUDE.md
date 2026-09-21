# hub — 허브

스포크 사이의 계약(포트 ABC와 DTO)만 가진다. 구현은 스포크가 제공한다.

- 어떤 스포크도 import하지 않는다 (`.importlinter`의 허브 격리 계약).
- 포트는 실제로 쓰는 스포크가 생길 때 추가한다. 빈 껍데기 포트를 미리 만들지 않는다.
- 구현하는 스포크는 HTTP 표면이 없는 슬라이스로 만들고, 인터랙터가 포트 ABC를 직접 상속한다.
- 소비하는 스포크는 `dependencies/hub_ports.py`의 자리로 받는다. `main.py`가 구현을 꽂는다.

| 포트 | 구현 | 사용 |
|---|---|---|
| `ShopAccessPort.resolve(user_id, shop_id) → ShopContext` | tenancy `resolve_shop_access` | 매장 범위의 모든 스포크 (`core/shop_guard.py`) |
| `ShopProvisioningPort.create_shop(name, business_type) → ProvisionedShop` | tenancy `provision_shop` | platform_admin `create_shop` |
| `MembershipDirectoryPort.list_for_user(user_id) → list[MembershipSummary]` | tenancy `list_memberships` | auth `get_me` |
| `OperatorDirectoryPort.is_operator(user_id) → bool` | auth `check_operator` | platform_admin |
| `UserDirectoryPort.get_profiles(user_ids) → dict[int, UserProfile]` | auth `get_user_profiles` | tenancy `list_members` |
| `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |

`MembershipLifecyclePort`(회원 탈퇴)는 계획 2-2에서 첫 소비자와 함께 들어온다.
