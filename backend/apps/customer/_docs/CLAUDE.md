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
- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각). `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
- 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
