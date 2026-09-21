# 002 — 허브 포트 조립 위치, Factory 표기, 계획 2 분할

- 날짜: 2026-09-20
- 근거: `001-plan1-review-carryover.md`의 3번·12번 항목, 계획 2 작성 중 사용자 결정

## 허브 포트 구현은 진입점이 꽂는다

`get_me`는 tenancy가 구현한 `MembershipDirectoryPort`가, tenancy의 멤버 목록은 auth가 구현한 `UserDirectoryPort`가 필요하다. `auth/dependencies/`가 `tenancy.adapter…`를 import하면 "스포크 상호 독립" 계약을 어긴다.

검토한 안은 셋이다. ① 진입점에서 조립 ② 허브에 레지스트리 ③ `*.dependencies`를 계약의 예외로 둔다. **①로 정했다.**

- 소비하는 스포크는 `dependencies/hub_ports.py`에 "자리" 함수를 둔다. 자리는 호출되면 `RuntimeError`를 던진다.
- `backend/main.py`(필요해지면 `auth_main.py`)가 `app.dependency_overrides[자리] = 구현 프로바이더`로 채운다. 진입점은 이미 모든 스포크를 import하는 유일한 곳이다.
- 구현 프로바이더가 `DbSession`을 받으면 같은 요청의 세션을 공유한다. 스포크를 넘는 작업도 한 트랜잭션으로 묶인다.
- 매장 접근 확인(`ShopAccessPort`) 자리는 모든 매장 범위 스포크가 쓰므로 `core/shop_guard.py`에 둔다. core가 허브의 추상(ABC·DTO)을 import하는 것은 허용한다. core가 스포크를 import하는 것은 여전히 금지다.
- 자리를 채우지 않은 실수는 `tests/test_hub_port_binding.py`와 실제 배선 통합 테스트가 잡는다.

②를 버린 이유: 허브가 "포트와 DTO만 가진다"는 규칙에서 벗어나 상태를 갖게 되고, 요청 단위 DB 세션을 넘길 방법을 따로 만들어야 한다. ③을 버린 이유: 스포크 간 결합이 조립 코드에 숨고 계약이 그만큼 약해진다.

## `factory/` 폴더의 패턴 표기를 "Factory"로 완화한다

`auth/adapter/outbound/factory/`의 `SocialProviderFactory`는 제공자별 인스턴스를 담아 두고 이름으로 골라 주는 객체이고, `build_social_provider_factory`는 설정을 보고 그 객체를 만드는 단순 팩토리다. GoF의 Factory Method(하위 클래스가 생성을 결정)와는 다르다. 폴더 이름과 코드는 그대로 두고 대응표의 패턴 칸만 "Factory"로 고친다. 제공자마다 Creator 클래스를 두는 구조로 바꾸면 클래스만 늘고 얻는 기능이 없다.

## 계획 2를 둘로 나눈다

계획 2(매장·RBAC·계정 연결·탈퇴)를 2-1(매장과 매장별 RBAC)과 2-2(계정 연결·해제, 회원 탈퇴, 제공자 연결 끊기, 리프레시 토큰 세대 번호)로 나눴다. 2-2는 2-1을 구현한 뒤 실제 코드를 보고 쓴다. `MembershipLifecyclePort`는 첫 소비자(`withdraw`)가 생기는 2-2에서 만든다.

## 001의 넘김 항목 처리 현황 (계획 2-1 종료 시점)

| 항목 | 처리 |
|---|---|
| 1 실제 배선 통합 테스트 | 계획 2-1 Task 2·17 (`backend/tests/integration/`) |
| 2 시드와 픽스처 충돌, 4 ORM 등록 목록 | 계획 2-1 Task 1 (`scripts/prepare_test_db.py`, `orm_registry.py`, `tests/test_schema_drift.py`) |
| 3 스포크 간 조립 위치 | 이 문서. 진입점에서 조립 |
| 12 Factory 표기 | 이 문서. 표기만 완화 |
| 24·26 설계 문서·문구 정정, 25 README | 계획 2-1 Task 17 |
| 5~10, 18~23 | 계획 2-2 (계정 연결·해제, 회원 탈퇴와 함께) |
| 11 재사용 감지 유예 | 결정됨 — 두지 않는다 |
| 13~17 | 운영 전환 때 |

## 계획 2-1에서 새로 미룬 것

- **직원이 스스로 매장을 나가는 기능.** 지금은 사장이 내보내야 한다. 설계에 없어서 만들지 않았다.
- **초대 코드 목록·무효화.** `shop_invites.revoked_at` 컬럼과 도메인 검사는 있으나 무효화하는 슬라이스가 없다. 7일 만료와 1회 사용으로 충분한지 Hiss Haus 투입 뒤에 본다.
- **초대 코드 해시에 서버 비밀값(pepper)을 섞지 않았다.** DB를 읽을 수 있는 공격자는 이미 그 매장의 데이터를 읽을 수 있고, 코드는 7일·1회용이라 얻는 것이 작다.
- **닫힌 매장·정지된 매장을 만드는 기능.** `closed_at`은 회원 탈퇴(계획 2-2)가, `suspended_at`은 이후 운영자 기능이 쓴다. 지금은 읽기만 한다.
- **`/v1/me`의 매장 목록에 정지된 매장이 나온다.** 들어가면 `SHOP_SUSPENDED` 안내를 받는다. 앱(계획 3)에서 표시를 정한다.
