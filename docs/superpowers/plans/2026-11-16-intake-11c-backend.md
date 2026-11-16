# ⑪-C1 백엔드 — 첫 방문 문진표 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매장이 문진표 링크를 보내면 보호자가 로그인 없이 아이의 정보를 적어 내고, 사장은 받은 문진표를 보고 한 번 눌러 고객·반려동물로 등록한다. 다시 치는 칸이 없다.

**Architecture:** 전부 `customer` 스포크다. 서류 요청 표(`customer_forms`)의 `kind='intake'` 를 쓰고 답은 새 표 `intake_answers` 에 "받은 문진표"로 둔다 — **고객·반려동물 표를 건드리지 않는다.** 등록·반영은 기존 유스케이스(`register_customer`·`add_pet`·`update_pet`)가 하고, 요청 본문의 `intake_answer_id` 로 같은 트랜잭션에서 답을 지운다. 공개 경로는 동의서와 같은 관문(`open_form`)·같은 토큰(`X-Form-Token`)이다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic(0021).

**Spec:** `docs/superpowers/specs/2026-11-16-consent-intake-design.md`(3.1·3.4·3.6·3.7·5.2~5.5·6절), 공통(1·2·9·12절). 결정 기록 `_docs/decisions/014-consent-intake.md`.

**이 계획에 없는 것(다음 계획 ⑪-C1b)**: 문진표 끝에서 동의서까지(맡아 두는 서명, `consent_for_all`). 그 뒤 ⑪-C2 웹, ⑪-C3 앱.

## Global Constraints

- **보내는 곳 셋**: (가) `new` 새 손님 — `customer_id`·`pet_id` 없음. (나) `add_pet` 등록된 고객의 새 아이 — `customer_id`. (다) `update` 이미 있는 아이 — `pet_id`.
- **칸**(설계 3.4 의 표): 보호자 이름(50)·전화번호((가)에서만 묻고 필수) / 아이 이름(50, 필수) / 종·품종(50)·성별·중성화 / 생일 또는 태어난 해 또는 `몰라요` / 몸무게 또는 `모르겠어요` / 지병(종류 목록 + 기타 30자) 또는 `없어요`, 지병마다 한 줄(100) / 싫어하는 것(200) / 원하는 스타일(200) / 매장이 더한 질문의 답(200) / 개인정보 안내 동의(필수).
- **매장이 끌 수 있는 칸**(`intake_hidden`): `species`·`breed`·`sex`·`neutered`·`birth`·`weight`·`dislikes`·`style`. 보호자·아이 이름·지병·안내는 끌 수 없다.
- **매장이 더하는 질문**: 5개까지, 질문 글 100자, 필수 여부. 지운 질문의 행은 남긴다(`removed_at`).
- **(다)는 지금 값을 공개 화면에 싣지 않는다** — 아이 이름만. 모든 칸이 선택이다(바뀐 것만).
- **한 링크에 아이는 10마리까지.** (다)는 한 번 내면 닫힌다. (가)·(나)는 `done` 을 보내거나 10마리가 차거나 기간이 지나면 닫힌다. 둘째 답부터 보호자 칸은 첫 답의 것을 쓴다.
- **빈칸을 지어내지 않는다.** 끈 칸·`모르겠어요` 는 NULL 로 두고 등록 때 사장에게 묻는다(앱).
- **번호가 같은 고객을 미리 찾아 둔다**((가)) — `matched_customer_id`. 잠그지 않고 읽는다.
- **확인하지 않은 답은 기본 30일 뒤 지운다**(7~90일, 서류 설정 `intake_keep_days`). API 프로세스의 주기 작업(하루 한 번, `system_context`)이 지우고, 그 전이라도 읽을 때는 없는 것으로 친다. 지운 수만 로그에 적는다.
- 익명화: 그 고객의 문진표 요청을 끊고 `matched_customer_id` 가 그 고객인 답을 지운다. 반려동물 삭제·무지개다리: 그 아이의 (다) 요청을 끊는다.
- 권한: 보내기·등록·지우기 `customer:write`, 읽기는 매장 멤버, 설정·질문은 `shop:update`.
- 공개 스키마는 매장용과 따로 쓰고 칸을 하나하나 적는다. **싣지 않는 것**: ID(질문 ID 는 싣는다 — 답이 가리킨다), 전화번호, 지금 값, 메모, 주의·노쇼.
- **토큰·주소·적은 이름·전화번호·문진표의 글을 로그·오류 메시지·예외 문자열에 남기지 않는다.**
- 공개 제출은 동의서와 같은 한도(본문 131,072바이트, 접속 주소당 10분에 10번).
- 잠금: (나)·(다) 고객 행 → 서류 요청 행. (가)는 요청 행만.

## Review Focus

1. **같은 번호로 두 번 낸다 / 이미 등록된 번호로 낸다** → 답은 둘 다 받고, 등록된 고객이 미리 골라져 있다. 새 고객으로 등록하려 하면 번호 중복(기존 409)이다 — 조용히 덮어쓰지 않는다.
2. **보낸 뒤 매장이 칸을 끄거나 질문을 지운다** → 열려 있던 링크는 다음에 열 때 새 구성이다. 지운 질문의 답이 온 제출은 그 답만 버린다(422 로 통째로 막지 않는다).
3. **답을 등록하는 사이 다른 기기가 같은 답을 등록·지운다** → 둘째는 404(`INTAKE_ANSWER_NOT_FOUND`)이고 고객이 둘 생기지 않는다.
4. **끊은·기간 지난·다 채운 링크로 낸다** → 410. 10마리째 다음은 410.
5. **(다)의 답에 든 지병이 지금 없는 종류 코드다 / 길이를 넘는 글이다** → 422, 아무것도 쓰지 않는다. 오류 글에 적은 글이 없다.

---

### Task 1: 표·설정·질문

**Files:** `alembic/versions/0021_intake.py`, ORM `adapter/outbound/orm/intake_orm.py`(+`orm_registry.py`), `domain/value_objects/form_settings.py`(+`intake_keep_days: int = 30`, `intake_hidden: tuple[str, ...] = ()`), `domain/services/form_settings_rules.py`(범위 7~90, 모르는 칸 코드 422), `form_settings_pg_repository.py`·`form_settings_schema.py`(**PUT 에서 두 칸은 선택 — 빠지면 지금 값을 둔다**, 응답과 `defaults` 에는 늘 싣는다), 질문 슬라이스 `list_intake_questions`·`update_intake_questions`(`GET·PUT /v1/shops/{id}/intake-questions` — PUT 은 목록 전체 `[{question_id|null, label, required}]`, 빠진 질문은 `removed_at`), 저장소 `intake_question_repository`.

- 표: `customer_forms.intake_pet_id`(FK pets, 부분 유일 `WHERE kind='intake' AND revoked_at IS NULL AND submitted_at IS NULL`), `shop_form_settings.intake_keep_days smallint NOT NULL DEFAULT 30`·`intake_hidden varchar(20)[] NOT NULL DEFAULT '{}'`, `shop_intake_questions(id, shop_id, position, label varchar(100), required bool, removed_at)`, `intake_answers`, `intake_answer_conditions(answer_id, position, type_code, custom_label, note)`, `intake_answer_extras(answer_id, question_id, body varchar(200))`.
- [ ] 단위·통합(RED): 기본값, 범위, 모르는 칸, 예전 앱의 다섯 칸 PUT 이 새 칸을 지우지 않는다, 질문 5개·101자·빈 글·순서·지우기(행은 남는다)·직원 403·다른 매장.
- [ ] 구현 → GREEN → 스키마 대조 → 커밋.

### Task 2: 문진표 보내기와 보낸 서류

**Files:** `domain/entities/intake.py`(`IntakeForm{…, mode}`, `IntakeAnswer`), 저장소 `intake_form_repository`(create·live_for·get·lock·find_public·list_live·revoke·mark_submitted·close_for_customer·close_for_pet), 유스케이스 `issue_intake_form`(`POST /v1/shops/{id}/intake-forms {customer_id|null, pet_id|null}` → `{form_id, url, expires_on, sent_on}`, 201/200), `list_forms`(문진표도 싣는다 — `kind: "intake"`, `mode`, 새 손님은 `customer_id`·`customer_name` 이 null), `revoke_form`(종류를 가리지 않는다), 익명화·삭제·무지개다리 잇기.

- (나)·(다)는 같은 대상의 살아 있는 요청이 있으면 같은 링크(200). (가)는 늘 새 링크(201).
- [ ] 통합(RED): 셋의 발급, 같은 링크, 없는 고객·아이 404, 익명화한 고객 404, 무지개다리 아이 422, 보낸 서류에 함께 보임(응답 칸 고정), 끊기, 익명화·삭제가 끊는다, 직원 가능·다른 매장 404, 로그에 주소 없음.
- [ ] 구현 → GREEN → 커밋.

### Task 3: 공개 읽기와 제출

**Files:** `read_public_form_interactor.py`(종류로 가른다), `app/services/intake_reader.py`, 유스케이스 `submit_public_intake`(`POST /v1/public/form/intake`), `public_form_schema.py`(문진표 응답·요청), `domain/services/intake_rules.py`(칸 검증 — 순수 함수), `tests/route_inspection.py` 의 허용 목록과 프로세스별 목록 테스트.

- 공개 응답(열림): `{kind:"intake", state:"open", shop:{name}, mode, pet_name|null, fields:[켜진 칸 코드], questions:[{question_id,label,required}], condition_types:[{code,label}], answered:int}`. 닫힘·낸 뒤는 동의서와 같다(`submitted`).
- 제출 본문: `{guardian:{name,phone}|null, pet:{name, species, breed, sex, neutered, birth_date, birth_year, birth_unknown, weight_kg, weight_unknown, no_known_conditions, conditions:[{type_code,custom_label,note}], dislikes, style}, extras:[{question_id, body}], privacy_agreed, done}` → 204 / 404 / 410 / 413 / 422 / 429.
- 검증: (가)·(나)는 켜진 칸이 필수(생일 셋 중 하나, 몸무게 둘 중 하나, 지병은 `없어요` 나 하나 이상), 끈 칸은 받아도 버린다. (다)는 전부 선택. 필수 질문의 답이 비면 422. `privacy_agreed` 는 true 여야 한다.
- [ ] 단위(RED): 칸 검증의 갈래. 통합(RED): 열기·내기·둘째 아이(보호자 칸 물려받기)·`done`·10마리·(다) 한 번·번호 연결·끈 칸·지운 질문의 답·공개 응답의 칸 목록 고정·알림장 토큰 404·크기·횟수·로그에 이름·번호·글 없음.
- [ ] 구현 → GREEN → 커밋.

### Task 4: 받은 문진표와 등록

**Files:** 유스케이스 `list_intake_answers`(`GET …/intake-answers` → `{items:[{answer_id, mode, pet_name, guardian_name, submitted_on, matched_customer_id, matched_customer_name}]}`), `get_intake_answer`(`GET …/intake-answers/{id}` — 답 전부, 빈 필수 칸의 목록 `missing`, 메모 초안 `memo_draft`), `delete_intake_answer`(DELETE), `register_customer`·`add_pet`·`update_pet` 요청의 선택 칸 `intake_answer_id`(같은 트랜잭션에서 답을 지운다 — 없거나 다른 매장이면 404 `INTAKE_ANSWER_NOT_FOUND` 이고 아무것도 쓰지 않는다), `app/services/form_sweeper.py`(주기 작업 — `main.py` 의 lifespan), 익명화가 답을 지운다.

- 메모 초안: `조심할 것: … / 원하는 스타일: … / {질문}: …`. 500자를 넘어도 자르지 않는다(넘친 글자 수 `memo_over`).
- 보존 기한이 지난 답은 목록·한 장에서 없는 것으로 친다.
- [ ] 통합(RED): 목록·한 장(칸 고정)·지우기·등록이 답을 지운다·두 번 등록 404·다른 매장 404·번호가 같은 고객이 미리 골라져 있다·기한 지난 답은 없다·주기 작업이 지우고 수만 로그에 적는다·익명화가 지운다·검색 이벤트는 기존 쓰기가 낸다.
- [ ] 구현 → GREEN → 커밋.

### Task 5: 흐름·문서

- [ ] `backend/scripts/check_intake_flow.sh`: 설정 없이 보내기 → 로그인 없이 열기 → 내기 → 받은 문진표 → 등록(답이 사라짐) → 새 아이 → 다시 받기 → 칸 끄기·질문 더하기 → 익명화 뒤 없음.
- [ ] 루트 `CLAUDE.md`(명령어·`public_context` 가 쓰는 표에 `intake_answers`), `_docs/harness.md`, 014 에 "⑪-C1 백엔드에서 정한 것"과 API 계약 → 전체 단위·통합·계약·흐름 → 커밋.
