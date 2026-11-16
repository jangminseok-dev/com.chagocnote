# ⑪-C1b 문진표 끝에서 동의서까지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 첫 방문 보호자가 **링크 하나에서** 문진표와 미용 동의서를 함께 끝낸다. 답으로 보아 노령이거나 지병을 골랐으면(또는 매장이 `모든 아이에게` 를 켰으면) 문진표 아래에 동의서 구역이 나타나고, 그 서명은 아이 없이 맡아 두었다가 사장이 등록·반영할 때 그 아이에게 옮겨 붙는다.

**Architecture:** 백엔드(`customer` 스포크) — 서명 표가 "맡아 둔 서명"을 담는다(`customer_id` 없음, `intake_answer_id` 로 답에 매달림, 받은 길 `intake`). 답이 지워지면 함께 지워지고(외래 키 CASCADE), 등록·반영이 답을 쓸 때 먼저 떼어 내(`intake_answer_id` 를 비움) 새 아이에게 붙인 뒤 덮는 토막 계산으로 받은 날을 찍는다. 웹은 문진표 화면 끝에 기존 서명 칸(`SignaturePad`)을 붙인다. 앱은 받은 문진표 한 장에 서명 여부를 보이고, 서류 설정에 스위치 하나, 서명 보기에 받은 길 하나를 더한다.

**Tech Stack:** FastAPI · SQLAlchemy asyncio · Alembic(0023) / Next.js 16 · Vitest · Playwright / Flutter · Riverpod 3.

**Spec:** `docs/superpowers/specs/2026-11-16-consent-intake-design.md` 3.4 의 "문진표 끝에서 동의서까지"·3.3(서명·덮는 토막)·5.2(`consent_signatures.intake_answer_id`, `consent_signature_pets.pet_id null`)·5.3(`POST /v1/public/form/intake` 의 선택 `consent`)·5.4(등록의 트랜잭션 안에서 옮김)·F13. 앞선 결정은 `_docs/decisions/014-consent-intake.md`.

## Global Constraints

- **동의서 구역이 나타나는 답**: 매장의 `intake_consent_all`(서류 설정 `첫 방문 문진표에서 모든 아이에게 동의서 받기`, 기본 꺼짐)이 켜졌거나, 답의 생일·태어난 해로 그날(매장 시간대) 나이가 매장의 노령 나이(`senior_age`) 이상이거나, 지병을 하나 이상 골랐다. 토막은 `basic` 늘 + `senior`(노령) + `condition`(지병). 나이를 모르거나 칸이 꺼졌으면 노령이 아니다. 나이 계산은 백엔드 `pet_age.age_years` 와 같은 규칙이다.
- 지병 이름 목록은 글 밖에서 늘 따로 그린다(`알려 주신 지병: …`). 체크 문장은 `위 내용을 읽었고 동의해요`. 이름(1~50자)·서명·체크가 필수다.
- 낼 때 **매장의 글·노령 나이·`모든 아이에게` 가 연 뒤 바뀌었으면 409**(`CONSENT_DOCUMENT_CHANGED`) — 웹은 적은 답을 그대로 두고 다시 읽는다. 동의서가 나타나야 하는 답인데 서명이 없거나 필요한 토막을 읽지 않았으면 422(`CONSENT_REQUIRED`). 둘 다 답도 저장하지 않는다.
- 맡아 둔 서명은 **고객 표·반려동물 표를 건드리지 않는다**(문진표의 규칙 그대로). 받은 날은 등록·반영할 때 찍는다 — 그 아이에게 살아 있는 동의가 없을 때만, **서명한 날**(매장 시간대)로. 살아 있는 동의가 있으면 받은 날을 옮기지 않고 덮는 것만 는다.
- 맡아 둔 서명은 **자기가 보인 지병 이름과 토막만 덮는다** — 사장이 등록하며 지병을 더하거나 나이를 바꿨으면 남은 토막이 확인할 것에 `partial` 로 남는다(덮는 토막 계산이 알아서 한다).
- 답이 지워지면(지우기·보관 기간·익명화) 맡아 둔 서명도 사라진다. 등록이 실패해 되돌아가면 서명도 맡아 둔 채로 남는다.
- **서명 그림·적은 이름·토큰·문진표의 글을 로그·오류 메시지·예외 문자열·테스트 출력·스크린샷 설명에 남기지 않는다.** 화면에 "AI"·"법적 효력"이 없다. 앱은 네이티브·해요체·`print` 금지.

## Review Focus

1. **보호자가 문진표를 여는 사이 매장이 동의서 글이나 노령 나이를 바꿨다** → 409, 웹은 적은 답·이름을 지우지 않고 바뀐 글을 다시 보인다(서명만 다시).
2. **사장이 등록하면서 지병을 더하거나 생일을 고쳤다** → 맡아 둔 서명은 자기가 보인 것만 덮고, 남은 토막이 `partial` 로 남는다. 받은 날은 서명한 날이다.
3. **답이 지워졌다(지우기·보관 기간·익명화) / 등록이 실패했다** → 맡아 둔 서명이 고아로 남지 않고, 실패한 등록은 서명을 잃지 않는다.
4. **이미 살아 있는 동의가 있는 아이를 다시 받기로 반영했다** → 받은 날을 옮기지 않는다. 손으로 적은 동의면 그대로 덮는다.
5. **서명 그림이 64KB 를 넘거나 깨졌다 / 이름이 비었다 / 노령이 아닌데 웹이 서명을 보냈다** → 앞의 둘은 422 이고 답도 저장되지 않는다. 마지막은 받는다(읽은 토막 그대로 남긴다).

---

### Task 1: 백엔드 — 문진표에서 서명을 받아 맡아 둔다

**Files:** `backend/alembic/versions/0023_intake_consent.py`, `customer/domain/services/intake_consent.py`(새), `customer/domain/entities/{form_settings,consent_form}.py`, 서명·설정 저장소와 ORM, `customer/app/services/intake_reader.py`·`read_public_form`, `submit_public_intake_interactor.py`, 공개 스키마·DTO, 서류 설정 스키마(`intake_consent_all`). Test: `apps/customer/tests/domain/test_intake_consent.py`, `tests/integration/test_public_intake_wiring.py`, `test_intake_settings_wiring.py`, `tests/test_schema_drift.py`.

**Interfaces — Produces:**
- 마이그레이션 0023: `shop_form_settings.intake_consent_all bool not null default false` · `consent_signatures.customer_id` null 허용 · `consent_signatures.intake_answer_id bigint null → intake_answers.id ON DELETE CASCADE`(색인) · 받은 길 CHECK 에 `intake` · CHECK `customer_id IS NOT NULL OR intake_answer_id IS NOT NULL`.
- `intake_consent.py`: `consent_parts(entry: CleanAnswer, *, on: date, policy: ConsentPolicy, for_all: bool) -> tuple[str, ...]`(빈 튜플 = 동의서가 없다), `texts_digest(texts: dict[str, ConsentText], policy, for_all) -> str`(sha256 hex — 토막별 출처·판, 노령 나이, `for_all`).
- 공개 `GET /v1/public/form`(문진표)에 `consent: {all: bool, senior_age: int, texts: {basic|senior|condition: {body}}, digest: str}`.
- 공개 `POST /v1/public/form/intake` 의 선택 `consent: {digest, parts: [str], signer_name, signature_png(base64)}` → 204 / 409 `CONSENT_DOCUMENT_CHANGED` / 422 `CONSENT_REQUIRED`·검증.
- 서류 설정 `GET·PUT /form-settings` 에 `intake_consent_all`(PUT 에서 빠지면 지금 값).

- [ ] 단위(RED): 노령 경계(9·10살, 매장 노령 8살), 생일 모름·태어난 해만, 지병 0/1, `for_all` 켬 → `('basic',)`, 아무것도 아니면 `()`. 지문은 글의 판·노령 나이·`for_all` 하나만 바뀌어도 다르다.
- [ ] 통합(RED): 공개 읽기에 `consent` 가 실린다(지병 메모·ID 없음) / 12살 아이 + 서명 → 204, 답 하나·맡아 둔 서명 하나(`customer_id` 없음, 아이 칸 비어 있음, 토막 `basic`·`senior`, 받은 길 `intake`) / 같은 답에 서명 없음 → 422, 답 없음 / 연 뒤 매장이 글을 고침 → 409, 답 없음 / 그림이 PNG 가 아님 → 422 / 노령이 아닌데 서명 → 204(받는다) / 설정 PUT 이 `intake_consent_all` 을 바꾸고 빠지면 둔다.
- [ ] 구현 → GREEN → 스키마 대조·계약·단위·통합 → 커밋 `feat(intake): 문진표에서 동의서 서명을 받아 맡아 둔다`.

### Task 2: 백엔드 — 등록·반영이 맡아 둔 서명을 그 아이에게 옮긴다

**Files:** `customer/app/services/intake_answers.py`(`consume_answer` 가 떼어 낸 서명 ID 를 돌려준다), `customer/app/services/held_consent.py`(새 — `adopt_held_signature`), `register_customer`·`add_pet`·`update_pet` 유스케이스와 배선, 받은 문진표 한 장의 응답(`consent`), 흐름 `backend/scripts/check_intake_consent_flow.sh`(새). Test: `tests/integration/test_intake_answers_wiring.py`(또는 새 `test_intake_consent_wiring.py`).

**Interfaces:**
- Consumes: Task 1 의 표·`consent_parts`.
- Produces: `consume_answer(...) -> int | None`(맡아 둔 서명 ID — 답에서 떼어 냈다), `adopt_held_signature(ctx, signature_id, *, customer_id, pet_id, today, policy, pets, signatures) -> None`. `GET /intake-answers/{id}` 에 `consent: {signed_on: date, parts: [str]} | null`(그림·이름은 싣지 않는다).

- [ ] 통합(RED): 새 손님 답(12살 + 서명)으로 등록 → 그 아이의 서명 목록에 하나(받은 길 `intake`), `grooming_consent_on` = 서명한 날, 확인할 것에 동의 없음 / 등록하며 지병을 더함 → `consent` 가 `partial`(남은 토막 `condition`) / 등록 실패(번호 409) → 서명이 맡아 둔 채 남는다 / 답 지우기·보관 기간·익명화 → 맡아 둔 서명이 없다 / 살아 있는 서명 동의가 있는 아이의 다시 받기 → 받은 날 그대로 / 받은 문진표 한 장에 `consent`.
- [ ] 구현 → GREEN → 흐름 스크립트(시작에 개발 Redis 의 제출 횟수 키를 지운다) → 단위·통합·계약·흐름(`check_intake_flow.sh`·`check_consent_flow.sh` 도) → 문서(`apps/customer/CLAUDE.md`, 014 의 계약, `_docs/harness.md`, 루트 `CLAUDE.md` 명령 줄) → 커밋 `feat(intake): 등록·반영이 맡아 둔 동의서 서명을 그 아이에게 옮긴다`.

### Task 3: 웹 — 문진표 끝의 동의서 구역

**Files:** `web/lib/form.ts`(`OpenIntake.consent`), `web/lib/intake.ts`(`consentPartsOf(form, draft, today)`, `problemOf` 가 이름·서명·체크를 본다, `bodyOf` 가 `consent` 를 싣는다), `components/IntakeForm.tsx`(구역·409), `Intake.module.css`, `tests/intake.test.ts`·`IntakeForm.test.tsx`, `tests/server/{fake-backend,check}.mjs`, `tests/e2e/intake.spec.ts`, `web/CLAUDE.md`.

- [ ] 단위(RED): `consentPartsOf` 가 백엔드와 같은 경계(9·10살, 노령 나이 8, 모름, 꺼진 칸, 지병, `all`) / 구역이 있을 때만 `problemOf` 가 이름·서명·체크를 묻는다 / `bodyOf` 의 `consent` 에 `digest`·`parts` / 구역이 없으면 `consent` 가 없다.
- [ ] 컴포넌트(RED): 12살로 고르면 구역(토막 글·지병 이름·이름·서명 칸·체크)이 나타나고 9살이면 없다 / 이름 칸은 보호자 이름으로 미리 채워진다 / 409 면 `내용이 바뀌었어요. 다시 읽어 주세요` 와 다시 읽기, 적은 답은 남고 서명만 비운다 / [다른 아이도 적기] 뒤 서명이 비어 있다.
- [ ] 구현 → GREEN → `pnpm test`·`pnpm build`·`pnpm check:server`(문진표 열기에 `consent` 가 지나간다, 409 를 그대로 넘긴다)·`pnpm e2e`(노령 아이 + 서명 제출) → 커밋 `feat(intake): 웹 — 문진표 끝의 동의서 구역`.

### Task 4: 앱 — 설정 스위치, 받은 문진표의 서명, 받은 길

**Files:** `form_settings_models.dart`(`intakeConsentAll`), `form_settings_screen.dart`(스위치 + 한 줄 설명 + 보호자가 받는 모습에 동의서 줄), `intake_models.dart`(`IntakeAnswer.consent`), `received_intake_screens.dart`(한 장의 `동의서` 구역 — `서명했어요 · 11월 16일 · 미용 안내 · 노령`, `등록하면 이 아이의 동의로 남아요`), `consent_models.dart`(`SignatureChannel.intake`), `consent_signatures_screen.dart`(받은 길 문구), `app_strings.dart`, `tool/prepare_intake_flow.sh`(12살 답 + 서명), `integration_test/intake_flow_test.dart`(등록 뒤 동의 줄이 `서명 받음`), `app/CLAUDE.md`.

- [ ] 위젯(RED): 스위치를 누르면 설정 전체를 보내고 `intake_consent_all` 이 바뀐다(직원은 못 누름) / 서명이 있는 답의 한 장에 동의서 구역, 없으면 없다 / 받은 길 `intake` 의 서명 줄·한 장 문구 / 모르는 받은 길은 여전히 버린다.
- [ ] 구현 → GREEN → `flutter analyze`·`flutter test` → 시뮬레이터 흐름 iOS·안드로이드 → 문서 → 커밋 `feat(intake): 앱 — 문진표 동의서 스위치·받은 문진표의 서명·받은 길`.

### 끝

- 최종 검토(새 맥락, model fable, 이 계획의 Review Focus) → Critical·Important 는 테스트 먼저 한 번의 수정 → 014 에 "⑪-C1b 에서 정한 것" → 메모리 → 보고(병합 메뉴).
