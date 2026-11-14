# customer — 고객(보호자), 반려동물, 질병, 검색

소유 데이터: `customers`, `pets`, `pet_condition_types`(시드), `pet_conditions`, `customer_search_entries`(검색용 역정규화).

- 고객(사람)이 기본이고 반려동물은 선택적인 하위 대상이다. 반려동물은 고객을 거쳐 매장에 속한다 — `pets`에 `shop_id`를 두지 않는다.
- `customers.shop_id`는 tenancy의 매장 ID지만 외래 키를 걸지 않는다. 스포크 안의 관계(고객 → 반려동물 → 질병)는 외래 키를 건다.
- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 매장과 상관없는 `ConditionTypeRepository.list_all()`만 예외다. 반려동물은 언제나 반려동물 → 고객(살아 있음) → 매장 순서로 소속을 거른다. 다른 매장의 ID는 404다.
- 표는 3NF다. 역정규화는 `customer_search_entries` 하나뿐이고, 원본은 언제나 `customers`·`pets`다. 응답의 보호자·반려동물 정보는 원본에서 읽는다.
- **가족(고객·반려동물·질병)을 바꾸는 유스케이스는 맨 앞에서 고객 행을 잠근다.** 고객 경로는 `CustomerRepository.lock_active`, 반려동물 경로는 `PetRepository.lock_owner`(반려동물 → 고객 행). 잠금이 없으면 익명화와 겹친 반려동물 추가가 익명화한 고객에게 이름을 되살리고, 마지막 두 마리를 동시에 지워 반려동물 없는 가족이 남는다. 잠금 순서는 고객 행 → 반려동물 행이다. customer 경로는 tenancy의 행(유저·매장·멤버·초대)을 잠그지 않는다.
- 같은 트랜잭션 안에서 `CustomerSearchPort.rebuild_search_entry(ctx, customer_id)`로 그 가족의 검색 줄을 다시 만든다. 익명화한 고객이면 줄을 지운다. 어긋나면 `scripts/rebuild_customer_search.py`로 복구한다.
- 검색은 `CustomerSearchPort` 뒤에 있다(지금은 PostgreSQL `pg_trgm`). 전용 검색 엔진으로 바꿀 때 어댑터만 바꾼다. LIKE 특수 문자는 어댑터가 이스케이프한다.
- 전화번호는 숫자만 저장한다. 매장 안에서 살아 있는 고객끼리 유일하다(부분 유일 색인 `uq_customers_shop_phone_active` — 동시에 두 번 와도 하나만 성공, 늦은 쪽은 409). 보조 연락처는 중복 판단에 쓰지 않는다.
- 목록과 반려동물 상세의 번호는 가린다(`010-12··-5678`). 전체 번호는 고객 상세에서만 준다. 전화번호·이름을 로그에 남기지 않는다. 검색어와 번호 조회는 쿼리 문자열로 오므로 API 프로세스가 접근 로그의 쿼리를 가린다(`core/access_log.py`).
- 고객 삭제는 익명화다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행을 지우고 `deleted_at`을 찍는다. 행과 틀(종류·품종·성별 등)은 남긴다. 익명화한 고객은 모든 조회·검색·번호 조회에서 없는 것으로 본다.
- 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각·카톡 초안 후보, notification 의 연락처). `contact(ctx, customer_id)`는 살아 있는 이 매장의 고객만 이름·전체 번호(숫자만)·마케팅 동의를 돌려주고 익명화·다른 매장이면 None 이다 — 알림을 보내는 순간에만 읽고(notification), 저장하지 않는다. 초안 후보(`find_draft_candidates`)는 낱말 하나라도 걸리는 가족(`CustomerSearchPort.match_any`, OR)을 읽어 반려동물 이름 정확 일치 → 보호자 이름 → 전화 → 부분 일치 순으로 최대 5 가족만 돌려주고, 낱말을 저장하거나 로그에 남기지 않는다. `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
- 반려동물 프로필 사진은 저장하지 않는다. 조회 셋(목록 `pets[].photo`, 고객 상세 `pets[].photo`, 반려동물 상세 `pet.photo`)이 읽을 때마다 `VisitLedgerPort.latest_covers`(대표 사진의 media_id)와 `MediaLibraryPort.read_urls`(썸네일 URL)로 한 번씩 묻는다(`app/services/pet_photos.py`, N+1 없음). 쓰기 응답에는 사진이 없다 — 쓰기 뒤 다시 읽는다. `MediaLibraryPort`는 `dependencies/hub_ports.py`의 자리로 받는다.
- 익명화는 visit 이 방문 메모와 미용 기록의 두 메모(케어·내부)를 비우고 그 고객 방문의 알림장 링크를 끊는다(⑤). 사진은 매장의 기록이라 남긴다. 미용 기록의 몸무게는 visit 이 `CustomerDirectoryPort.set_pet_weight`로 알려 준다(가장 최근 기록일 때만) — 고객 행을 잠근 트랜잭션 안이다.
- 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
- **미용 동의와 주의 표시**(③-B)는 새 표가 아니라 칸이다(0016) — 둘 다 "지금의 것 하나"이고 이력이 없다. 규칙은 `domain/services/care_marks.py` 의 순수 함수다.
  - **미용 동의**: `pets.grooming_consent_on`(가장 최근에 받은 날)·`grooming_consent_by_member_id`. `PUT·DELETE /pets/{pet_id}/grooming-consent`(`customer:write` — 직원도). 받은 날을 주지 않으면 오늘, 앞날은 422. 노령·지병이 아닌 아이와 무지개다리 아이에게도 적을 수 있다(막지 않는다). **반려동물 수정에서 지병이 하나라도 늘면 동의를 비운다**(`conditions_added` — (종류, 직접 적은 이름)으로 견준다. 빼거나 메모만 고친 것은 아니다) — 앞서 받은 동의가 새 지병을 덮지 않게.
  - **주의 표시**: `customers.caution_reason`(1~100자, 앞뒤 공백을 뗀 뒤)·`caution_until`·`caution_set_at`·`caution_set_by_member_id` — 넷은 함께 있거나 함께 없다(CHECK). `PUT·DELETE /customers/{customer_id}/caution`(`customer:write`). 달거나 고치면 끝나는 날은 오늘로부터 365일 뒤다. 푸는 것은 멱등이다. **기한이 지난 표시는 지우지 않고 읽을 때 거른다**(`caution_active` — 끝나는 날 당일까지 살아 있다). 상세·목록·`care_facts` 가 같은 함수를 쓴다. 주의 표시는 `updated_at`(최근순)을 건드리지 않고 검색 줄도 다시 만들지 않는다.
  - 보이는 곳: 고객 상세 `customer.caution {reason, until}`, **반려동물 상세 `caution`**([보호자] 탭이 이 응답으로 그린다)과 `pet.grooming_consent_on`, 목록의 줄 `caution: bool`(사유는 싣지 않는다). 보호자 경로·공개 스키마에는 칸이 없다.
  - **익명화가 주의 칸 넷과 그 고객 반려동물의 동의 칸 둘을 비운다.** 주의 사유는 사람에 대한 평가다 — 로그·오류 메시지에 남기지 않는다(본문 검증 오류에도 되돌려 싣지 않는다).
  - 주의·동의의 '오늘'은 이 스포크의 다른 곳처럼 `seoul_today` 다(매장 시간대가 아니다).
- 허브 포트 `CustomerDirectoryPort.care_facts(ctx, customer_ids, pet_ids, today)` — visit 의 "확인할 것"의 재료. 살아 있는 이 매장의 고객(`known_customers`), 살아 있는 주의 표시(`today` 기준), 아이의 생일·출생 연도·지병(이름은 기타면 직접 적은 이름, 메모)·동의 받은 날·무지개다리. **`briefs` 와 달리 익명화한 고객과 그 아이는 틀도 주지 않는다.** 아이는 그 보호자가 `customer_ids` 에 있어야 나온다. 고객이 몇이든 읽는 횟수가 같다(고객 한 번, 아이 한 번, 지병 한 번).
