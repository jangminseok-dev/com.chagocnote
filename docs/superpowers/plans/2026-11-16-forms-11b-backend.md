# ⑪-B 백엔드 — 서류 설정·매장이 고치는 문안·보낼 것 묶음 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매장이 동의서의 글과 기준값(링크 기간·노령 나이·동의 기한)을 자기 가게에 맞게 고치고, 한 예약에 보호자에게 보낼 글(예약 안내 + 동의서 링크)을 서버가 한 묶음으로 조립해 준다.

**Architecture:** 서류 설정과 문안은 `customer` 스포크의 새 표 둘(`shop_form_settings`·`shop_consent_texts`)이다. ⑪-A 가 비워 둔 자리 셋 — `consent_policy()`, `current_texts()`, `visit_checks` 의 상수 — 을 매장의 값으로 채운다. 묶음 조립은 `visit` 이고 서류 링크는 새 허브 포트 `GuardianFormPort` 로 받는다(visit 은 customer 를 import 하지 않는다).

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic(0020).

**Spec:** `docs/superpowers/specs/2026-11-16-consent-intake-design.md`(3.1·3.2·3.5·3.6 의 6·5.2·5.3·10절), 공통 `2026-11-16-next-designs-common.md`(1·3·4·12절). 결정 기록 `_docs/decisions/014-consent-intake.md`.

## Global Constraints

- 기본값: 링크 14일(1~30) · 노령 10살(5~20) · 동의 기한 365일(30~1095). **행이 없으면 기본값이다** — 아무것도 건드리지 않아도 돈다.
- 문안은 토막마다 2,000자까지, 비워 저장할 수 없다(되돌리기는 `body: null`). 고치면 새 판이 쌓이고 옛 판은 지우지 않는다. **이미 받은 동의를 다시 받게 하지 않는다.**
- 보내는 글의 템플릿은 500자까지, 비울 수 없다. 자리는 `{매장}`·`{아이}`·`{날짜}`·`{시간}`·`{메뉴}`·`{링크}` 뿐이다 — 모르는 `{…}` 는 422. 동의서 템플릿에는 `{링크}` 가 꼭 있어야 한다. **빈칸이 든 글은 나가지 않는다.**
- 설정·문안 쓰기는 `shop:update`(사장), 읽기는 매장 멤버. 묶음 조립은 `reservation:write`.
- 매장이 고친 문안·템플릿·주소·토큰을 로그·오류 메시지·예외 문자열에 남기지 않는다.
- 잠금: 고객 행 → 서류 요청 행. 묶음 조립은 방문 행을 잠그지 않는다.
- 스포크끼리 import 하지 않는다. 화면 글에 "AI"·"법적 효력"이 없다.

## Review Focus

1. **노령 기준을 낮춘다(10 → 8)** → 8살 아이의 다음 예약에 `consent` 가 뜨고, 서명으로 받은 동의면 `partial`(senior 만)이다. 이미 받은 동의의 받은 날은 그대로다.
2. **문안을 고친 직후 보호자가 옛 문안을 보던 링크로 낸다** → 409(지문이 다르다). 옛 서명 보기는 옛 글자 그대로다.
3. **링크 기간을 줄인다** → 이미 낸 링크의 기간은 그대로다. 새 링크부터다.
4. **메뉴가 없는 예약·보호자만의 예약의 묶음** → `{메뉴}`·`{아이}` 가 든 줄이 빈칸으로 나가지 않는다.
5. **끝났거나 취소된 방문·익명화한 고객의 방문의 묶음** → 토막이 없다(링크도 만들지 않는다).

---

### Task 1: 서류 설정 — 표·값·API, 기준값이 매장의 값을 읽는다

**Files:** Create `alembic/versions/0020_form_settings.py`, `customer/domain/value_objects/form_settings.py`, `customer/domain/services/form_settings_rules.py`, `customer/app/ports/output/form_settings_repository.py`, `customer/adapter/outbound/pg/form_settings_pg_repository.py`, ORM(`adapter/outbound/orm/form_settings_orm.py` + `orm_registry.py`), 유스케이스 `get_form_settings`·`update_form_settings`(포트·DTO·provider·router·schema `form_settings_schema.py`). Modify `customer/dependencies/customer_wiring.py`, `ConsentPolicy` 를 받는 유스케이스 다섯(issue·get_document·sign_in_shop·read_public·submit_public).

**Interfaces — Produces:**
- `FormSettings(link_days, senior_age, consent_days, reservation_text: str | None, consent_text: str | None)` · `DEFAULT_FORM_SETTINGS = (14, 10, 365, None, None)` · `.policy -> ConsentPolicy`.
- `check_form_settings(settings)` — 범위 밖·템플릿 규칙 위반이면 `CustomerInputError`(422). `DEFAULT_RESERVATION_TEXT`·`DEFAULT_CONSENT_TEXT`·`PLACEHOLDERS`.
- `FormSettingsRepository.get(ctx) -> FormSettings`(없으면 기본값, 행을 만들지 않는다) · `put(ctx, settings) -> FormSettings`(upsert).
- `GET·PUT /v1/shops/{id}/form-settings` → `{link_days, senior_age, consent_days, reservation_text, consent_text, defaults: {link_days, senior_age, consent_days, reservation_text, consent_text}}`. `reservation_text`·`consent_text` 는 지금 쓰는 글(고치지 않았으면 기본 글)이고, PUT 에서 `null` 이면 기본 글로 되돌린다.
- `ConsentPolicy` 를 생성자로 받던 유스케이스는 `settings: FormSettingsRepository` 를 받아 `(await settings.get(ctx)).policy` 로 읽는다.

- [ ] 단위(RED): 범위(0·31일, 4·21살, 29·1096일), 템플릿(빈 글·501자·모르는 자리·`{링크}` 없는 동의서 글), `.policy`.
- [ ] 통합(RED): 행이 없으면 기본값·GET 이 행을 만들지 않는다 / PUT 뒤 GET / 직원은 403 / 다른 매장의 값이 섞이지 않는다 / **링크 기간 3일로 바꾼 뒤 낸 링크의 `expires_on` 이 3일 뒤이고 먼저 낸 링크는 그대로** / **노령 8살로 바꾸면 8살 아이의 문서에 senior 토막**.
- [ ] 구현 → GREEN → 전체 단위·통합·계약 → 커밋.

### Task 2: 매장이 고치는 문안

**Files:** 0020 에 `shop_consent_texts` 포함. Create `customer/app/ports/output/consent_text_repository.py`, `adapter/outbound/pg/consent_text_pg_repository.py`, 유스케이스 `list_consent_texts`·`update_consent_text`(router·schema `consent_text_schema.py`). Modify `customer/app/services/consent_reader.py`(`current_texts` 가 저장소를 읽는다), `get_consent_signature_interactor.py`(옛 판의 글자), `read_document` 를 부르는 곳.

**Interfaces — Produces:**
- `ConsentTextRepository.latest(ctx) -> dict[part, (version, body | None)]` · `body_of(ctx, part, version) -> str | None` · `append(ctx, part, body | None) -> int`(다음 판, 멤버·시각 포함).
- `current_texts(ctx, texts)`(async) — 매장의 최신 판이 글이면 `ConsentText("shop", version, body)`, 없거나 `body null` 이면 기본 글.
- `GET /v1/shops/{id}/consent-texts` → `{parts: [{part, body, edited: bool, default_body}]}`(문서의 순서) · `PUT …/consent-texts/{part}` `{body: str | null}` → 그 토막. 지금 글과 같으면 판을 쌓지 않는다. 모르는 토막 404.

- [ ] 단위(RED): 글 검사(빈 글·공백만·2,001자), 같은 글이면 쌓지 않는다.
- [ ] 통합(RED): 고친 글이 문서·공개 읽기에 보인다 / **고친 뒤 옛 지문으로 내면 409** / **옛 서명 보기는 옛 글자** / 되돌리면 기본 글이고 판은 쌓인다 / 고쳐도 이미 받은 동의는 그대로(`consent` 가 다시 뜨지 않는다) / 직원 403 / 다른 매장의 글이 보이지 않는다.
- [ ] 구현 → GREEN → 커밋.

### Task 3: ③-B 의 판정이 매장의 값을 읽는다

**Files:** Modify `hub/app/dtos/care_facts.py`(`CareFacts.senior_age: int = 10`, `consent_days: int = 365`), `customer/app/use_cases/customer_directory_interactor.py`(설정을 읽어 싣는다), `visit/domain/services/visit_checks.py`(상수 대신 인자), `visit/app/services/visit_checks.py`, `visit/domain/value_objects/check_facts.py`.

- [ ] 단위(RED): 노령 8살 설정에서 8살 아이에게 `consent`, 기한 30일 설정에서 31일 지난 동의가 `expired`. 기본값이면 ③-B 의 기존 테스트가 그대로 통과.
- [ ] 통합(RED): 설정을 바꾼 매장의 확인할 것(하루 목록의 `확인 N` 포함)이 바뀌고 다른 매장은 그대로.
- [ ] 구현 → GREEN → `check_visit_checks_flow.sh` → 커밋.

### Task 4: 보낼 것 묶음

**Files:** Create `hub/app/ports/guardian_form_port.py`, `customer/app/use_cases/guardian_form_interactor.py`, `visit/domain/services/send_bundle.py`, `visit/app/use_cases/build_send_bundle_interactor.py`(포트·DTO·provider·router `build_send_bundle_router.py`·schema). Modify `visit/dependencies/hub_ports.py`, `main.py`, `tests/route_inspection.py` 의 표.

**Interfaces — Produces:**
- `GuardianFormPort.consent_link(ctx, pet_ids, for_date) -> str | None` — 살아 있는 요청이 있으면 그 주소, 없으면 만든다. 더 받을 것이 없으면 `None`. `bundle_texts(ctx) -> BundleTexts(reservation, consent)`(매장의 템플릿).
- `build_bundle(shop_name, pets: [이름], starts_at(매장 시간대), menus: [이름], texts, consent_url) -> list[BundlePart(kind, text)]` 순수 함수. **값이 빈 자리(`{메뉴}`·`{아이}`)가 든 줄은 뺀다.** `consent_url` 이 없으면 `consent` 토막이 없다.
- `POST /v1/shops/{id}/visits/{visit_id}/send-bundle` → `{parts: [{kind, text}]}`. 그 방문의 가족 묶음(같은 보호자·같은 시작 시각의 살아 있는 방문들)을 한 묶음으로 조립한다. 예약 상태(`reserved`)가 아니면 `parts: []`. 없는 방문 404.

- [ ] 단위(RED): 자리 채우기, 메뉴 없는 예약, 보호자만의 예약, 가족 둘(`초코 · 라떼`), 링크 없음, 매장이 고친 템플릿.
- [ ] 통합(RED): 노령 아이의 예약 → 토막 둘이고 링크가 살아 있는 요청과 같다(두 번 불러도 같은 주소) / 동의가 필요 없는 아이 → `reservation` 뿐 / 완료·취소된 방문 → 빈 목록 / 다른 매장의 방문 404 / 응답의 주소가 로그에 없다.
- [ ] 구현 → GREEN → 계약(import-linter) → 커밋.

### Task 5: 흐름·문서

- [ ] `backend/scripts/check_consent_flow.sh` 에 줄을 더한다: 설정 기본값 → 문안 고치기 → 공개 읽기에 고친 글 → 옛 지문 409 → 묶음(토막 둘) → 노령 기준 바꾸기 → 확인할 것이 바뀜.
- [ ] 루트 `CLAUDE.md`(명령어 설명), `_docs/harness.md`, 014 에 "⑪-B 백엔드에서 정한 것"과 API 계약.
- [ ] 전체: 단위·통합·계약·흐름 넷(consent·visit_checks·report·guardian) → 커밋.
