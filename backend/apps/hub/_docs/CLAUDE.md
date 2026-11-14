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
| `CustomerDirectoryPort.contact(ctx, customer_id) → CustomerContact \| None` (이름·번호(숫자만)·마케팅 동의, 익명화면 None) | customer `customer_directory` | notification 만 (보내는 순간의 연락처 — `briefs` 는 가린 번호라 못 쓴다) |
| `CustomerDirectoryPort.care_facts(ctx, customer_ids, pet_ids, today) → CareFacts` (살아 있는 고객, 살아 있는 주의 표시, 아이의 나이·지병·미용 동의·무지개다리. 익명화한 고객과 그 아이는 틀도 없이 빠진다) | customer `customer_directory` | visit 만 (확인할 것 ③-B — 방문이 몇 개든 한 번) |
| `DomainEventPort.publish(event)` | core `observer/in_process_event_bus.py` (같은 프로세스·같은 세션의 동기 버스, 구독자 목록은 `main.py` 가 기동 때 채운다) | 발행 visit (등록·수정·일정 변경·전이·알림장 보내기), 구독 notification (`adapter/inbound/observer/`) |
| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기(`clear_customer_memos` — 알림장 링크도 끊는다)·`latest_covers`) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세, 반려동물 프로필 사진) |
| `MediaLibraryPort.claim(ctx, ids) → {id: kind} · release · read_urls(ctx, ids) → {id: MediaUrls}` | media `media_library` | visit (기록의 사진·영상, 알림장), customer (프로필 사진) |
| `ShopProfilePort.public_profile(shop_id) → ShopProfile \| None` (이름·전화·주소·시간대·영업 중 여부) | tenancy `get_shop_profile` | visit (알림장의 매장 정보, 공개 조회의 시간대와 정지·폐업 판정), notification (보낼 때의 매장 이름·시간대·`shop_closed` 판정, 실패 줄의 `share_text`) |

- `MediaUrls`에는 `download_url`이 있다 — 원본을 첨부 파일로 내려받는 서명 주소다. 칸이 `original_url` 바로 뒤라 `MediaUrls`는 이름 인자로 만든다.
- `ShopProfilePort.public_profile`은 권한을 보지 않고 정지·폐업한 매장도 돌려준다(`None`은 없는 매장뿐). 로그인한 사용자가 없는 경로가 서명을 확인한 링크에서 읽은 매장 ID 로만 부른다. notification 의 디스패처도 요청 밖에서 집은 줄의 매장 ID 로 부른다.
- 이벤트 DTO 는 `app/dtos/visit_events.py`의 여섯 — `VisitReserved(revived)`, `VisitRescheduled(previous_starts_at)`, `VisitCanceled(reason)`, `VisitClosed(outcome, previous_completed_at)`, `VisitReportIssued(url, expires_at)`, `VisitReportRevoked`(칸 없음). 공통 칸은 `ctx`(발행한 요청의 `ShopContext`)·`visit_id`·`customer_id`·`pet_id`·`starts_at`·`occurred_at`(UTC), 그리고 하위 클래스마다 맨 끝의 `family_pet_ids: tuple[int, ...] = ()`(그 명령이 함께 다룬 같은 보호자·같은 시작 시각 방문들의 `pet_id`, 오름차순 — 가족 묶음을 알림톡 한 통으로 묶는 데 쓴다. frozen dataclass 상속 때문에 바탕 클래스가 아니라 하위 클래스 끝에 둔다). 구독자는 발행한 인터랙터와 같은 세션·같은 트랜잭션에서 돌고, **구독자가 던지면 발행한 요청이 실패한다**(의도 — 둘이 어긋나지 않게). `VisitReportIssued.url` 에는 토큰이 든다 — 이벤트를 `%r` 로 로그에 찍지 않는다.
- notification 은 요청 안에서도 `ShopProfilePort`·`CustomerDirectoryPort` 를 쓴다(`dependencies/hub_ports.py` 의 자리, `share_text`). 요청 밖의 디스패처는 `Depends` 자리를 못 쓰므로 같은 세 프로바이더(tenancy·customer·visit)를 `dependencies/dispatcher_ports.py` 의 공장 자리로 받고 `main.py` 가 꽂는다.
