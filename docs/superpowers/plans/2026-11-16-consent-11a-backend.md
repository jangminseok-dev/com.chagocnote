# ⑪-A 전자 동의서 — 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보호자가 로그인 없이 링크에서, 또는 매장에서 사장 폰으로 미용 동의서에 서명하고, 그 서명이 `consent` 확인 항목을 저절로 지우며, 노령·지병이 바뀌면 바뀐 토막만 다시 받게 한다.

**Architecture:** 서류는 전부 `customer` 스포크에 산다. 알림장이 쓰던 토큰·접속 주소·횟수 제한·공개 컨텍스트를 `core/`·`hub/` 로 올려 `customer` 가 함께 쓴다(동작은 그대로). 무엇이 덮였는지는 서명 기록에서 읽고, 판정은 지금처럼 `visit` 의 `visit_checks` 가 방문의 날을 기준으로 한다 — `customer` 는 사실(서명이 덮는 것)만 허브 DTO 로 준다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic(head 0017 → 0018) · Redis(횟수 제한) · pytest. 전부 `infra/` 에서 Docker Compose 로 돌린다.

**Spec:** `docs/superpowers/specs/2026-11-16-consent-intake-design.md`(⑪), `docs/superpowers/specs/2026-11-16-next-designs-common.md`(공통 — 어긋나면 이쪽이 앞선다)

## 이 계획의 범위

⑪ 을 셋으로 나눈 첫 단계의 백엔드다(사용자 승인 2026-11-16: ⑪-A 동의서 → ⑪-B 한 번에 보내기·서류 설정 → ⑪-C 문진표).

- **한다**: 올리기 넷, 표와 마이그레이션, 기본 문안·조립·덮는 것 계산·지문, 동의서 발급·보낸 서류·끊기, 현장 서명, 공개 읽기·서명, 서명 보기, 익명화·삭제·무지개다리·지병 수정·손 표시와의 잇기, `PetCareFact` 와 `visit_checks` 의 `partial`, 흐름 스크립트, 문서.
- **하지 않는다(뒤 단계)**: 매장이 고치는 문안·링크 기간·노령 기준·동의 기한(⑪-B — 이 계획은 기본값 14일·10살·365일을 **인자로 받는 자리**만 만든다), 보낼 것 묶음과 `GuardianFormPort`(⑪-B), 문진표·맡아 둔 서명·주기 작업(⑪-C), 웹(⑪-A2)·앱(⑪-A3).

## Global Constraints

- 주석·문서·테스트 이름·커밋 메시지는 한국어. 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·main 병합은 사용자가 말할 때만.
- 과금되는 것·외부 서비스 연결이 없다. 새 비밀값이 없다(`REPORT_LINK_KEY` 를 쓴다).
- 스포크끼리 import 하지 않는다. `customer` 는 `visit` 을 import 하지 않는다. `core/` 는 허브의 추상만 import 한다.
- 매장 범위의 저장소 메서드는 `ShopContext` 가 첫 인자다. 가드 없이 `ShopContext` 를 만드는 곳은 `hub/app/dtos/shop_context.py` 의 `public_context`·`system_context` 둘뿐이다.
- 로그인 없는 경로는 `tests/route_inspection._PUBLIC_ROUTES` 와 프로세스별 목록 테스트(`tests/test_hub_port_binding.py`)에 있는 것뿐이다. 공개 스키마는 매장용과 따로 쓰고 칸을 하나하나 적는다.
- 서류 토큰은 헤더 `X-Form-Token` 으로만 받는다. **토큰·주소·서명 그림·적은 이름·지병 이름을 로그·오류 메시지·예외 문자열에 남기지 않는다.** 로그는 `shop_id`·`form_id`·결과뿐이다.
- 잠금 순서: 고객 행(`pets.lock_owner` / `customers.lock_active`) → 서류 요청 행. 잠금을 쥔 채 외부 HTTP 를 부르지 않는다.
- 기준값(이 계획에서는 상수이고 함수는 인자로 받는다): 링크 기간 14일, 노령 10살, 동의 기한 365일, 서명 그림 600×240·65,536바이트 이하, 적은 이름 1~50자.
- 화면·문서·응답 어디에도 "법적 효력"·"AI" 라는 말을 쓰지 않는다.
- 검증 명령(`infra/` 에서): 단위 `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` · 통합 `… -m integration` · 계약 `docker compose run --rm --no-deps backend lint-imports --config .importlinter`.

## Review Focus

1. **지병이 하나에서 둘이 된 뒤 옛 화면으로 서명한다** → 409 이고 서명이 저장되지 않는다. (작업 5 의 통합 테스트)
2. **알림장 토큰을 서류 경로에, 서류 토큰을 알림장 경로에 넣는다** → 둘 다 404. (작업 1·5)
3. **부분 서명(바뀐 토막만)을 한다** → 받은 날이 옮겨지지 않고 기한이 처음 전체 서명에서 365일이다. (작업 2·4)
4. **익명화·반려동물 삭제 뒤** 서명 그림·적은 이름·보인 지병 이름의 행이 남지 않는다. (작업 6)
5. **같은 아이에게 [보내기]를 두 번, 동시에 누른다** → 링크가 하나다. 현장 서명을 받으면 살아 있던 링크는 그 아이를 덜어 내고, 아이가 남지 않으면 닫힌다. (작업 4)

---

### Task 1: 알림장의 공개 도구를 `core/`·`hub/` 로 올린다 (동작은 그대로)

**Files:**
- Create: `backend/core/link_token.py`, `backend/core/public_client.py`, `backend/core/public_redis_limiter.py`, `backend/apps/hub/app/ports/public_limiter_port.py`
- Modify: `backend/apps/hub/app/dtos/shop_context.py`(`public_context` 를 더한다), `visit` 의 쓰는 곳 전부(아래 목록), `CLAUDE.md`, `backend/apps/visit/_docs/CLAUDE.md`
- Delete: `backend/apps/visit/domain/services/report_token.py`, `backend/apps/visit/app/services/public_context.py`, `backend/apps/visit/dependencies/public_client.py`, `backend/apps/visit/app/ports/output/public_report_limiter_port.py`, `backend/apps/visit/adapter/outbound/redis/public_report_redis_limiter.py`
- Test: 옮긴 것의 테스트를 함께 옮긴다 — `backend/tests/test_link_token.py`, `backend/tests/test_public_client.py`, `backend/apps/hub/tests/…/test_public_context.py`(허브의 테스트 자리에 맞춘다)

**Interfaces:**
- Produces:
  - `core.link_token`: `new_public_id() -> bytes`, `make_token(public_id: bytes, key: bytes, purpose: bytes = b"") -> str`, `read_token(token, key: bytes, purpose: bytes = b"") -> bytes | None`, `TOKEN_LENGTH = 43`. 서명 대상은 `purpose + public_id` 다 — `purpose=b""` 이면 지금 알림장 토큰과 글자 하나 다르지 않다.
  - `hub.app.ports.public_limiter_port.PublicLimiterPort`: `allow(client) -> bool`, `note_miss(client) -> None`, `missed_too_much(client) -> bool`, **새** `allow_write(client) -> bool`(10분 창에 10번까지 — 서류 제출용, 알림장은 쓰지 않는다).
  - `core.public_redis_limiter.PublicRedisLimiter(redis, namespace: str)`: 키는 `{namespace}-hits:{해시}`·`{namespace}-misses:{해시}`·`{namespace}-writes:{해시}`. 알림장은 `namespace="visit:report"`(지금 키 그대로), 서류는 `"customer:form"`.
  - `core.public_client.get_public_client(request) -> str`(지금 것 그대로).
  - `hub.app.dtos.shop_context.public_context(shop: ShopProfile) -> ShopContext`(지금 것 그대로, 설명 글만 고친다 — 아래).

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `tests/test_link_token.py`

```python
def test_용도가_다르면_같은_public_id_의_토큰이_서로_읽히지_않는다():
    pid = new_public_id()
    report, form = make_token(pid, KEY), make_token(pid, KEY, b"form:")
    assert report != form
    assert read_token(report, KEY) == pid and read_token(form, KEY, b"form:") == pid
    assert read_token(report, KEY, b"form:") is None and read_token(form, KEY) is None

def test_용도를_주지_않은_토큰은_옮기기_전과_글자가_같다():
    # 옮기기 전 구현으로 미리 계산해 둔 값(고정 키·고정 public_id) — 보호자에게 이미 나간 링크가 그대로 열려야 한다.
    assert make_token(bytes(range(16)), b"k" * 32) == EXPECTED_BEFORE_MOVE
```

`EXPECTED_BEFORE_MOVE` 는 옮기기 **전에** 지금 `visit.domain.services.report_token.make_token` 으로 계산해 테스트에 적는다. 횟수 제한: `test_쓰기_제한은_10분에_10번까지다`(가짜 Redis 로 11번째가 False), `test_이름_공간이_다르면_서로의_수를_세지_않는다`.

- [ ] **Step 2: 실패를 본다** — Run: 단위 명령에 `tests/test_link_token.py` · Expected: FAIL `ModuleNotFoundError: core.link_token`

- [ ] **Step 3: 올린다** — 넷을 새 자리에 만들고 옛 파일을 지우고, 아래 쓰는 곳의 import 를 바꾼다(다른 것은 건드리지 않는다): `guardian/adapter/inbound/api/v1/claim_guardian_link_router.py`, `visit/adapter/inbound/api/v1/{mark_report_viewed,read_public_report}_router.py`, `visit/app/ports/output/guardian_report_repository.py`, `visit/app/services/{guardian_scope,public_report_gate,report_reader}.py`, `visit/app/use_cases/{mark_report_viewed,read_public_report,resolve_report_link,send_visit_report}_interactor.py`, `visit/dependencies/visit_wiring.py`, `visit/domain/entities/visit_report.py`, 그 테스트·가짜(`visit/tests/helpers/{fakes,public_world}.py`, `test_fakes_are_ports.py`). `guardian` 이 지금 `visit` 의 것을 어떻게 받는지 읽고 같은 방식으로 `core` 의 것을 받게 한다. `public_context` 의 설명 글: "로그인이 없는 공개 경로가 쓰는 매장 컨텍스트. 권한이 비어 있다. 읽기와, 공개 서류 제출이 쓰는 표에만 쓴다(루트 CLAUDE.md)."

- [ ] **Step 4: 루트 `CLAUDE.md` 를 고친다** — "가드 없이 `ShopContext`를 만드는 곳" 줄을 이렇게: 가드 없이 만드는 곳은 `hub/app/dtos/shop_context.py` 의 둘뿐이다 — 매장 멤버가 아닌 요청 경로(로그인 없는 공개 알림장·공개 서류, 로그인한 보호자의 읽기)에서는 `public_context`, 요청 밖에서는 `system_context`. 둘 다 권한이 비어 있다. `public_context` 는 포트 읽기와 **공개 서류 제출이 쓰는 표**(`customer_forms`·`consent_signatures` 와 그 아래 표, 서명이 찍는 `pets` 의 동의 칸 셋)에만 쓴다. "알림장 토큰은 헤더(`X-Report-Token`)로" 줄에 서류 토큰(`X-Form-Token`)을 더한다. 잠금 순서 줄에 "서류 쪽은 고객 행 → 서류 요청 행이다" 를 더한다.

- [ ] **Step 5: 전부 통과하는지 본다** — Run: 단위·통합·계약 세 명령 · Expected: 단위·통합 전부 PASS(옮기기 전과 개수가 같고 새 테스트만 늘었다), 계약 6 kept.

- [ ] **Step 6: 커밋** — `refactor(core): 알림장의 토큰·접속 주소·횟수 제한·공개 컨텍스트를 core·hub 로 올린다`

---

### Task 2: 문안·조립·덮는 것·지문 (순수 함수)

**Files:**
- Create: `backend/apps/customer/domain/services/consent_text.py`, `consent_document.py`, `consent_coverage.py`, `signature_image.py`; `backend/apps/customer/domain/value_objects/consent_document.py`(지금 `value_objects` 폴더가 없으면 `domain/entities/consent.py` 에 함께 둔다 — 스포크의 지금 관례를 따른다)
- Test: `backend/apps/customer/tests/domain/test_consent_document.py`, `test_consent_coverage.py`, `test_signature_image.py`

**Interfaces:**
- Produces:
  - `consent_text`: `PARTS = ("basic", "senior", "condition")`, `DEFAULT_VERSION = 1`, `default_body(part: str) -> str`. 글의 요지는 설계 3.2 의 표. 글자는 여기서 굳힌다 — 토막마다 3~5문장, 존댓말, "법적 효력" 없음.
  - `consent_document`:
    - `@dataclass(frozen=True) ConsentPolicy(senior_age: int = 10, consent_days: int = 365)`
    - `@dataclass(frozen=True) PetConsentFacts(pet_id, name, birth_date, birth_year, condition_labels: tuple[str, ...], consent_on: date | None, via_signature: bool, signed: tuple[SignedCover, ...], passed_away: bool)` — `SignedCover(parts: frozenset[str], condition_labels: frozenset[str])` 는 `consent_on` 뒤(그날 포함)의 서명 하나가 덮은 것.
    - `needed_parts(facts, on: date, policy) -> tuple[str, ...]` — `basic` 늘, `senior` 는 `age_on(...) >= policy.senior_age`(`customer.domain.services.pet_age` 의 나이 함수를 쓴다), `condition` 은 지병이 하나라도.
    - `@dataclass(frozen=True) DocumentPet(pet_id, name, condition_labels, parts: tuple[str, ...], full: bool)` — `parts` 는 **남은 토막**, `full` 은 이번 서명이 전체 서명인지(받은 날을 찍는지).
    - `build_document(pets: Sequence[PetConsentFacts], on: date, policy) -> tuple[DocumentPet, ...]` — 남은 토막이 없는 아이와 무지개다리 아이는 뺀다. `pet_id` 오름차순.
    - `doc_digest(doc: Sequence[DocumentPet], versions: Mapping[str, tuple[str, int]]) -> str` — `sha256` 16진수. 재료는 아이마다 `(pet_id, name, parts, [(part, source, version)], condition_labels)` 를 정한 순서로 JSON 으로 이은 것.
  - `consent_coverage.uncovered(facts, on, policy) -> tuple[tuple[str, ...], bool]` — (남은 토막, 전체를 다시 받아야 하는가).
    - 받은 날이 없거나 `(on - consent_on).days > policy.consent_days` → 필요한 토막 전부, `True`.
    - 서명으로 받았다(`via_signature`): `basic` 은 덮였다. `senior` 는 `signed` 가운데 `senior` 가 든 것이 있으면 덮였다. `condition` 은 지금 지병 이름이 모두 `signed` 의 지병 이름 합집합 안에 있으면 덮였다. `False`.
    - 손으로 적었다(`via_signature` 가 거짓): 남은 것이 없다, `False`. **(Ruling 예정 — 설계 3.3 은 "받은 날에는 노령이 아니었으면 전체를 다시"라 했고 F14 는 "손 표시의 규칙은 그대로"라 했다. F14 를 따른다: ③-B 의 지금 동작을 바꾸지 않는다.)**
  - `signature_image.check_png(raw: bytes) -> None` — PNG 머리 8바이트, IHDR 의 폭·높이(바이트 16~24)가 1 이상이고 600×240 이하, 길이 65,536 이하가 아니면 `CustomerInputError`. 그림을 풀지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# test_consent_document.py
def test_아홉_살은_basic_만_열_살은_senior_가_붙는다(): ...        # 생일 하루 전/당일
def test_지병이_있으면_condition_이_붙는다(): ...
def test_남은_토막이_없는_아이와_무지개다리_아이는_문서에서_빠진다(): ...
def test_지병이_하나에서_둘이_되면_지문이_다르다(): ...
def test_아이_이름이나_토막의_판이_바뀌면_지문이_다르다(): ...
def test_같은_사실이면_아이를_넣는_순서가_달라도_지문이_같다(): ...

# test_consent_coverage.py
def test_받은_날이_없으면_필요한_토막_전부이고_전체_서명이다(): ...
def test_삼백육십오일째는_덮이고_삼백육십육일째는_전부_다시다(): ...
def test_서명_뒤에_노령이_되면_senior_만_남는다(): ...             # full 은 False
def test_서명_뒤에_지병이_더해지면_condition_만_남는다(): ...
def test_더해진_지병을_덮는_부분_서명이_있으면_남은_것이_없다(): ...
def test_지병을_빼거나_메모만_고친_것은_남기지_않는다(): ...
def test_손으로_적은_동의는_토막을_가르지_않는다(): ...             # 노령이 돼도 남은 것이 없다
def test_기준값을_바꾸면_따라간다(): ...                           # ConsentPolicy(senior_age=8, consent_days=180)

# test_signature_image.py
def test_PNG_가_아니면_거절한다(): ...        # JPEG 머리, 빈 바이트
def test_폭이나_높이가_넘으면_거절한다(): ...  # 601×240, 600×241
def test_육만오천오백삼십육_바이트는_받고_하나_더_크면_거절한다(): ...
```

- [ ] **Step 2: 실패를 본다** — Expected: FAIL `ModuleNotFoundError`
- [ ] **Step 3: 구현한다** — 위 Interfaces 대로. 전부 순수 함수다(DB·시계를 모른다).
- [ ] **Step 4: 통과를 본다** — Run: 단위 명령에 `apps/customer/tests/domain` · Expected: PASS
- [ ] **Step 5: 커밋** — `feat(consent): 동의서의 기본 문안·조립·덮는 것 계산·지문`

---

### Task 3: 표·마이그레이션·저장소

**Files:**
- Create: `backend/alembic/versions/0018_consent_forms.py`, `backend/apps/customer/domain/entities/consent_form.py`, `backend/apps/customer/app/ports/output/{consent_form_repository,consent_signature_repository}.py`, `backend/apps/customer/adapter/outbound/orm/consent_orm.py`, `backend/apps/customer/adapter/outbound/pg/{consent_form_pg_repository,consent_signature_pg_repository}.py`
- Modify: `customer_orm.py`·`pet.py`·`customer_mapper.py`·`pet_repository.py`·`pet_pg_repository.py`(`grooming_consent_signature_id`), `customer_wiring.py`, 가짜(`apps/customer/tests/helpers`)
- Test: `backend/tests/integration/test_consent_schema.py`, `apps/customer/tests/test_fakes_are_ports.py`

**Interfaces:**
- 표(설계 5.2 에서 이 단계의 것만):
  - `customer_forms(id, shop_id, kind varchar(10) CHECK in ('consent','intake'), public_id bytea unique, customer_id bigint null, expires_at timestamptz not null, revoked_at, submitted_at, created_by_member_id bigint not null, created_at)` · `customer_form_pets(form_id, pet_id, PK 둘)`.
  - `consent_signatures(id, shop_id, customer_id, form_id bigint null unique, channel varchar(10) CHECK in ('link','in_shop'), signer_name varchar(50), signature_png bytea CHECK octet_length <= 65536, signed_at timestamptz, by_member_id bigint not null)`
  - `consent_signature_pets(id, signature_id, pet_id bigint null, shown_pet_name varchar(50))` · `consent_signature_parts(signature_pet_id, part varchar(10), text_source varchar(10) CHECK in ('default','shop'), text_version int, PK(signature_pet_id, part))` · `consent_signature_conditions(signature_pet_id, position smallint, label varchar(50), PK(signature_pet_id, position))`
  - `pets.grooming_consent_signature_id bigint null` + CHECK `grooming_consent_signature_id IS NULL OR grooming_consent_on IS NOT NULL`.
  - 스포크 사이 FK 는 두지 않는다. 같은 스포크 안의 FK 는 지금 `customer` 표들의 관례를 따른다(지울 때의 순서는 작업 6).
- Produces:
  - `ConsentForm(id, shop_id, public_id, customer_id, pet_ids: tuple[int, ...], expires_at, revoked_at, submitted_at, created_by_member_id, created_at)` · `is_live(now) -> bool`(끊지 않았고 내지 않았고 기간 안).
  - `ConsentFormRepository`: `create(ctx, customer_id, pet_ids, public_id, expires_at) -> ConsentForm` · `live_for_customer(ctx, customer_id, now) -> list[ConsentForm]`(행을 잠근다 — `FOR UPDATE`) · `list_live(ctx, now) -> list[ConsentForm]` · `get(ctx, form_id) -> ConsentForm`(없으면 `FormNotFoundError`) · `revoke(ctx, form_id, now)` · `mark_submitted(form_id, now)` · `set_pets(form_id, pet_ids)` · `find_public(public_id) -> ConsentForm | None`(매장을 가리지 않는 공개 읽기 — 서명을 확인한 `public_id` 로만 부른다) · `lock(form_id) -> ConsentForm | None`.
  - `ConsentSignatureRepository`: `add(ctx, signature: NewSignature) -> int` · `covers_for_pets(ctx, pet_ids) -> dict[int, tuple[SignedCover, ...]]`(아이의 `grooming_consent_on` 뒤의 서명만 — `signed_at` 을 매장 시간대의 날로 견준다) · `list_for_pet(ctx, pet_id) -> list[SignatureBrief]` · `get(ctx, signature_id) -> SignatureDetail`(없으면 `SignatureNotFoundError`) · `image(ctx, signature_id) -> bytes` · `delete_for_customer(ctx, customer_id) -> int` · `delete_for_pet(ctx, pet_id) -> int`.
  - `PetRepository.set_grooming_consent(ctx, pet_id, received_on, member_id, signature_id: int | None = None)` — 인자 하나를 더한다. `Pet.grooming_consent_signature_id`.

- [ ] **Step 1: 실패하는 통합 테스트** — `tests/integration/test_consent_schema.py`: `test_마이그레이션_뒤에_표와_제약이_있다`(표 여섯, CHECK 넷, `public_id` 유일), `test_서명_그림이_65537_바이트면_DB_가_거절한다`, `test_서명_없이_서명_ID_만_있는_동의는_DB_가_거절한다`, `test_다른_매장의_요청은_get_이_못_찾는다`, `test_covers_for_pets_는_받은_날_앞의_서명을_세지_않는다`.
- [ ] **Step 2: 실패를 본다** — Expected: FAIL(표가 없다)
- [ ] **Step 3: 마이그레이션·ORM·엔티티·저장소·가짜를 만든다.** `tests/test_schema_drift.py` 가 ORM 과 마이그레이션의 어긋남을 잡는다.
- [ ] **Step 4: 통과를 본다** — Run: 통합 명령에 `tests/integration/test_consent_schema.py`, 단위 전체 · Expected: PASS. 개발 DB 에 `docker compose run --rm backend alembic upgrade head` → `0018`.
- [ ] **Step 5: 커밋** — `feat(consent): 서류 요청과 서명의 표·저장소 (0018)`

---

### Task 4: 매장 쪽 유스케이스와 경로

**Files:** (슬라이스 1:1 — 유스케이스마다 `app/dtos`·`app/ports/input`·`app/use_cases`·`adapter/inbound/api/{schemas,v1}`·`dependencies` 한 벌)
- Create: `issue_consent_form`, `list_forms`, `revoke_form`, `get_consent_document`, `sign_consent_in_shop`, `list_pet_consent_signatures`, `get_consent_signature`, `get_consent_signature_image`, 그리고 함께 쓰는 `backend/apps/customer/app/services/consent_reader.py`·`consent_signer.py`
- Modify: `customer/domain/errors.py`, `customer/adapter/inbound/api/error_map.py`, `backend/main.py`
- Test: `apps/customer/tests/app/use_cases/test_*_interactor.py`(가짜 저장소), `apps/customer/tests/adapter/test_*_router.py`, `tests/integration/test_consent_wiring.py`

**Interfaces:**
- 오류(`code` → 상태): `FormNotFoundError` `FORM_NOT_FOUND` 404 · `FormClosedError` `FORM_CLOSED` 410 · `SignatureNotFoundError` `SIGNATURE_NOT_FOUND` 404 · `ConsentDocumentChangedError` `CONSENT_DOCUMENT_CHANGED` 409 · `ConsentUpToDateError` `CONSENT_UP_TO_DATE` 409(남은 토막이 하나도 없다) · `TooManyFormRequestsError` `TOO_MANY_REQUESTS` 429. 메시지에 이름·지병을 싣지 않는다.
- `consent_reader.read_document(ctx, pet_ids, today, policy, *, pets, signatures) -> tuple[tuple[DocumentPet, ...], dict[str, tuple[str, int, str]], str]` — (문서, 토막 → (source, version, body), 지문). 아이들은 **같은 고객**이어야 한다(아니면 `CustomerInputError`), 익명화한 고객·다른 매장의 아이는 `PetNotFoundError`.
- `consent_signer.sign(ctx, *, customer_id, pet_ids, doc_digest, signer_name, signature_png, channel, form_id, by_member_id, now, today, policy, …) -> int` — **고객 행을 이미 쥔 안에서** 부른다. 문서를 다시 읽어 지문이 다르면 `ConsentDocumentChangedError`. 서명 행을 쓰고, `full` 인 아이는 `set_grooming_consent(today, by_member_id, signature_id)`, 아닌 아이는 받은 날을 두고 서명만 는다. 그 고객의 살아 있는 요청에서 **이번에 서명한 아이를 덜어 내고** 아이가 남지 않으면 닫는다(링크 서명이면 그 요청은 `mark_submitted`).
- 경로와 권한:

| 경로 | 권한 | 응답 |
|---|---|---|
| `POST /v1/shops/{shop_id}/consent-forms` `{pet_ids: [int]}`(1~10) | `customer:write` | 201 `{form_id, url, expires_on, sent_on}` — 그 아이들을 모두 담은 살아 있는 요청이 있으면 200 으로 같은 것 |
| `GET /v1/shops/{shop_id}/forms` | 매장 멤버 | `{items: [{form_id, kind, customer: {customer_id, name}, pets: [{pet_id, name}], sent_on, expires_on, url}]}` 보낸 날 내림차순 |
| `DELETE /v1/shops/{shop_id}/forms/{form_id}` | `customer:write` | 204(이미 닫힌 것도 204) |
| `GET /v1/shops/{shop_id}/consent-document?pet_ids=1&pet_ids=2` | 매장 멤버 | `{pets: [{pet_id, name, conditions: [label], parts: [part]}], texts: {part: {body}}, previous_consent_on, doc_digest}` — 남은 것이 없으면 409 `CONSENT_UP_TO_DATE` |
| `POST /v1/shops/{shop_id}/consent-signatures` `{pet_ids, doc_digest, signer_name, signature_png(base64)}` | `customer:write` | 201 `{signature_id}` |
| `GET /v1/shops/{shop_id}/pets/{pet_id}/consent-signatures` | 매장 멤버 | `{items: [{signature_id, signed_at, channel, signer_name, parts: [part]}]}` 새것부터 |
| `GET /v1/shops/{shop_id}/consent-signatures/{signature_id}` | 매장 멤버 | `{signature_id, signed_at, channel, signer_name, by_member_id, pets: [{pet_id, shown_name, conditions: [label], parts: [{part, body}]}]}` — `body` 는 그 판의 글자 |
| `GET /v1/shops/{shop_id}/consent-signatures/{signature_id}/image` | 매장 멤버 | `image/png`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` |

- 발급의 규칙: `pets.lock_owner` 로 고객 행을 잠근다 → `live_for_customer` → 요청한 아이를 모두 담은 것이 있으면 그것, 없으면 요청한 아이를 담은 옛 요청들에서 그 아이를 덜어 내고(비면 닫고) 새 요청을 만든다 — **아이 하나에 살아 있는 동의서 요청은 하나다.** `expires_at = now + 14일`. `url = f"{REPORT_WEB_BASE_URL}/f/{make_token(public_id, REPORT_LINK_KEY, b'form:')}"`. 주소를 로그에 남기지 않는다.

- [ ] **Step 1: 실패하는 테스트** — 유스케이스(가짜)와 통합:

```python
# tests/integration/test_consent_wiring.py (게이트웨이 없이 앱에 직접)
async def test_같은_아이에게_두_번_보내면_같은_링크다(): ...
async def test_동시에_두_번_보내도_살아_있는_요청은_하나다(): ...          # asyncio.gather 두 요청
async def test_가족_두_마리를_한_요청에_담는다(): ...
async def test_다른_고객의_아이를_섞으면_422(): ...
async def test_현장_서명이_받은_날을_찍고_확인할_것에서_consent_가_사라진다(): ...
async def test_현장_서명을_받으면_살아_있던_링크에서_그_아이가_빠지고_비면_닫힌다(): ...
async def test_지문이_다르면_409_이고_서명_행이_없다(): ...
async def test_부분_서명은_받은_날을_옮기지_않는다(): ...                  # 지병 더한 뒤 condition 만
async def test_남은_토막이_없으면_발급도_문서도_409(): ...
async def test_직원은_보내고_서명받을_수_있고_다른_매장은_404(): ...
async def test_서명_그림은_png_로_그대로_돌아온다(): ...                   # 바이트가 같다, 헤더 둘
async def test_끊은_요청은_보낸_서류에_없다(): ...
async def test_응답과_로그에_토큰이_없다(): ...                            # caplog 에 주소·토큰·적은 이름이 없다
```

- [ ] **Step 2: 실패를 본다** — Expected: FAIL(404 — 경로가 없다)
- [ ] **Step 3: 구현하고 `main.py` 에 라우터를 더한다.** 오늘은 지금 `customer` 가 쓰는 `seoul_today` 방식이다.
- [ ] **Step 4: 통과를 본다** — Run: 단위·통합·계약 · Expected: PASS, 6 kept. `docker compose run --rm --no-deps auth python scripts/print_routes.py` 에 새 경로 여덟이 보이고 가드가 표와 같다.
- [ ] **Step 5: 커밋** — `feat(consent): 동의서 보내기·끊기·현장 서명·서명 보기`

---

### Task 5: 공개 읽기와 서명

**Files:**
- Create: `read_public_form`·`submit_public_consent` 두 벌(유스케이스·스키마·라우터·프로바이더), `backend/apps/customer/app/services/public_form_gate.py`
- Modify: `backend/main.py`, `backend/tests/route_inspection.py`(`_PUBLIC_ROUTES`), `backend/tests/test_hub_port_binding.py`(API 프로세스의 로그인 없는 경로 목록), `customer/dependencies/hub_ports.py`(`ShopProfilePort` 자리 — `visit` 이 받는 방식과 같게)
- Test: `apps/customer/tests/app/use_cases/test_{read_public_form,submit_public_consent}_interactor.py`, `tests/integration/test_public_form_wiring.py`

**Interfaces:**
- Consumes: 작업 1 의 토큰·횟수 제한·접속 주소·`public_context`, 작업 4 의 `consent_reader`·`consent_signer`.
- `public_form_gate.open_form(token, client, now, *, link_key, forms, shops, limiter) -> tuple[ConsentForm, ShopProfile]` — 알림장의 `open_report` 와 같은 순서다: `limiter.allow` → `read_token(token, key, b"form:")` → 틀리면 실패 수 차단을 보고 404 → `find_public` → 없으면 404 → 끊었거나 기간이 지났으면 410 → 매장이 닫혔으면 410. **낸 요청은 여기서 떨어뜨리지 않는다**(읽기가 `submitted` 를 보여야 한다).
- `GET /v1/public/form` 헤더 `X-Form-Token` → 200
  - 열려 있다: `{kind: "consent", state: "open", shop: {name}, previous_consent_on: date | null, pets: [{name, conditions: [label], parts: [part]}], texts: {part: {body}}, doc_digest}`
  - 냈다: `{kind: "consent", state: "submitted", shop: {name}, submitted_on}` — 낸 내용은 싣지 않는다.
  - 살아 있는데 남은 토막이 없다(그 사이 매장에서 받았다): `submitted` 와 같은 모양, `submitted_on` 은 null.
  - 헤더는 알림장의 공개 응답과 같은 셋(`Cache-Control: no-store`, `X-Robots-Tag: noindex`, `Referrer-Policy: no-referrer`).
- `POST /v1/public/form/consent` `{doc_digest, signer_name, signature_png}` → 204 / 409 `CONSENT_DOCUMENT_CHANGED` / 410 / 404 / 422 / 429(`allow_write`). 고객 행 → 요청 행을 잠그고 `consent_signer.sign(channel="link", form_id=…, by_member_id=form.created_by_member_id)`. 이미 낸 요청이면 410.
- **공개 스키마에 싣지 않는 것**: ID(고객·반려동물·매장·요청·서명), 전화번호, 지병 메모, 반려동물 메모, 주의·노쇼, 다른 가족의 아이. 테스트가 칸 목록을 고정한다.

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/integration/test_public_form_wiring.py
async def test_링크로_읽고_서명하면_받은_날이_찍히고_다시_열면_submitted_다(): ...
async def test_지병이_하나_더해진_뒤_옛_지문으로_내면_409_이고_서명이_없다(): ...   # Review Focus 1
async def test_두_번_내면_410(): ...
async def test_끊은_링크와_기간이_지난_링크는_410_틀린_토큰은_404(): ...
async def test_알림장_토큰은_서류_경로에서_404_서류_토큰은_알림장_경로에서_404(): ...  # Review Focus 2
async def test_열한_번째_제출은_429(): ...
async def test_공개_응답의_칸은_정해진_것뿐이다(): ...       # 키 집합을 그대로 견준다 — 열림·냄 둘 다
async def test_닫힌_매장의_링크는_410(): ...
async def test_익명화한_고객의_링크는_410(): ...
async def test_로그에_토큰과_적은_이름이_없다(): ...
# tests/test_hub_port_binding.py — API 프로세스의 로그인 없는 경로 목록에 둘이 더해진다
```

- [ ] **Step 2: 실패를 본다** — Expected: FAIL(404, 목록 테스트는 집합이 다르다)
- [ ] **Step 3: 구현한다.** 헤더가 없거나 이상해도 422 가 아니라 404 다(알림장과 같게 선택 값으로 받는다).
- [ ] **Step 4: 통과를 본다** — Run: 단위·통합·계약 · Expected: PASS, 6 kept
- [ ] **Step 5: 커밋** — `feat(consent): 로그인 없는 동의서 읽기와 서명`

---

### Task 6: 지금 있는 것과 잇기

**Files:**
- Modify: `customer/app/use_cases/{set_pet_grooming_consent,clear_pet_grooming_consent,update_pet,delete_customer,delete_pet,mark_pet_passed_away,customer_directory}_interactor.py` 와 그 프로바이더, `customer/app/services/detail_reader.py`·`get_pet_schema.py`, `hub/app/dtos/care_facts.py`, `visit/domain/value_objects/check_facts.py`, `visit/domain/services/visit_checks.py`, `visit/app/services/visit_checks.py`, `visit/adapter/inbound/api/schemas/check_view_schema.py`(설명 글)
- Test: 각 유스케이스의 단위 테스트, `apps/visit/tests/domain/test_visit_checks.py`, `tests/integration/test_consent_wiring.py`·`test_visit_checks_wiring.py`

**Interfaces:**
- 허브 DTO `PetCareFact` 에 칸 둘(기본값이 있어 지금 만드는 곳이 깨지지 않는다): `consent_cover: ConsentCover | None = None` — `ConsentCover(senior: bool, condition_labels: frozenset[str])`, 서명으로 받은 동의일 때만 값이 있다. `consent_form_sent_on: date | None = None` — **살아 있는 요청이 있을 때만**.
- `visit` 의 `PetFacts` 에 같은 뜻의 칸 둘. `visit_checks._consent` 는:
  - 받은 날이 없으면 `missing`, 기한이 지났으면 `expired`(지금 그대로).
  - 그 밖에 `consent_cover` 가 있으면: 남은 토막 = (`senior` 가 필요한데 덮이지 않음) + (`condition` 이 필요한데 지금 지병 이름 가운데 덮이지 않은 것이 있음). 하나라도 있으면 `state: "partial"`, `parts: [...]`.
  - `consent_cover` 가 없으면(손 표시) 지금 그대로 — 뜨지 않는다.
  - `detail` 에 늘 `form_sent_on` 을 더한다(없으면 null).
- 규칙:
  - 손으로 [받았어요](`set_pet_grooming_consent`): `signature_id` 를 비운다. [지우기]도 같다.
  - 지병이 는다(`update_pet`): 서명으로 받은 동의(`grooming_consent_signature_id` 가 있다)면 받은 날을 **지우지 않는다**. 손 표시면 지금처럼 지운다.
  - 익명화(`delete_customer`): 같은 트랜잭션에서 그 고객의 살아 있는 요청을 끊고 서명 행(그림·이름·보인 사실)을 지운다. `anonymize` 다음, 보호자 연결 끝내기 앞.
  - 반려동물 삭제: 살아 있는 요청에서 그 아이를 덜어 내고(비면 닫고) 그 아이의 서명 행을 지운다. 무지개다리: 덜어 내기만 한다(서명은 남는다).
  - 반려동물 상세 응답에 `grooming_consent_via: "signature" | "manual" | null`.

- [ ] **Step 1: 실패하는 테스트**

```python
# apps/visit/tests/domain/test_visit_checks.py
def test_서명으로_받은_동의는_노령이_되면_partial_senior_다(): ...
def test_서명이_덮지_않은_지병이_있으면_partial_condition_이다(): ...
def test_손으로_적은_동의는_노령이_돼도_뜨지_않는다(): ...          # ③-B 그대로
def test_보낸_날이_있으면_detail_에_실린다(): ...
# tests/integration/test_consent_wiring.py
async def test_서명_뒤에_지병을_더하면_받은_날은_남고_확인할_것은_partial_이다(): ...
async def test_손_표시_뒤에_지병을_더하면_받은_날이_지워진다(): ...   # 지금 동작
async def test_손으로_받았어요를_누르면_서명과의_이음이_끊긴다(): ...
async def test_익명화하면_서명과_요청의_행이_남지_않는다(): ...       # Review Focus 4 — 행 수
async def test_아이를_지우면_그_아이의_서명이_지워지고_링크에서_빠진다(): ...
async def test_무지개다리는_링크에서만_빠지고_서명은_남는다(): ...
async def test_끊은_요청은_form_sent_on_을_만들지_않는다(): ...
```

- [ ] **Step 2: 실패를 본다** — Expected: FAIL
- [ ] **Step 3: 구현한다.** ③-B 의 단위·통합이 그대로 통과해야 한다(F14).
- [ ] **Step 4: 통과를 본다** — Run: 단위·통합·계약 전체 · Expected: PASS, 6 kept. `bash ../backend/scripts/check_visit_checks_flow.sh` 가 그대로 통과한다.
- [ ] **Step 5: 커밋** — `feat(consent): 서명이 확인할 것을 지우고, 바뀐 토막만 다시 받는다`

---

### Task 7: 흐름 스크립트와 문서

**Files:**
- Create: `backend/scripts/check_consent_flow.sh`, `_docs/decisions/014-consent-intake.md`
- Modify: `backend/apps/customer/CLAUDE.md`(없으면 `_docs/CLAUDE.md` — 스포크의 지금 자리), `CLAUDE.md`(명령어 줄), `_docs/harness.md`

- [ ] **Step 1: 흐름 스크립트를 쓴다** — 게이트웨이(`http://127.0.0.1:8080`)로. 다른 흐름 스크립트의 로그인·매장 준비 방식을 그대로 쓴다. 줄마다 `ok`/`FAIL` 을 찍고 하나라도 틀리면 0 이 아닌 값으로 끝난다. **토큰·주소를 화면에 찍지 않는다.**
  1. 노령 아이(10살)와 지병 있는 아이를 가진 고객을 만든다 → 예약 → 확인할 것에 `consent · missing`
  2. 동의서 보내기 → 다시 보내기가 같은 `form_id`
  3. 공개 읽기(헤더로) → `open`, 토막이 `basic·senior`
  4. 서명 → 204 → 다시 읽기 `submitted` → 두 번째 서명 410
  5. 확인할 것에서 `consent` 가 사라졌다 → 반려동물 상세 `grooming_consent_via: signature`
  6. 지병을 하나 더한다 → 확인할 것 `consent · partial · [condition]`
  7. 현장 서명 문서 → `parts` 가 `condition` 뿐 → 서명 → `consent` 가 사라졌고 받은 날이 그대로다
  8. 서명 목록 2건, 그림 응답이 `image/png`
  9. 다른 아이에게 보낸 뒤 끊기 → 공개 읽기 410, 보낸 서류에 없다
  10. 알림장 토큰으로 서류 경로 404
  11. 익명화 → 서명 목록 404, 공개 읽기 410
- [ ] **Step 2: 돌린다** — Run: `bash ../backend/scripts/check_consent_flow.sh` · Expected: 전부 `ok`, 종료 값 0
- [ ] **Step 3: 문서를 쓴다** — 결정 기록 014(정한 것·Ruling·받아들인 한계·미룬 것, ⑪-B·⑪-C 가 기댈 API 계약), 스포크 규칙(서류의 로그 규칙·잠금·공개 스키마), 루트 `CLAUDE.md` 의 명령어에 `check_consent_flow.sh` 한 줄, `_docs/harness.md`.
- [ ] **Step 4: 전체를 다시 돌린다** — 단위·통합·계약·흐름(동의서·확인할 것·알림장·보호자 — 올리기가 깨뜨리지 않았는지) · Expected: 전부 PASS
- [ ] **Step 5: 커밋** — `test(consent): 동의서 흐름 스크립트. docs: 결정 기록 014, 규칙`
