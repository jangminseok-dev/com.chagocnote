# visit — 방문(예약부터 완료까지), 매장 일정, 메뉴표

소유 데이터: `visits`, `visit_menus`, `visit_shop_settings`, `visit_weekly_closures`, `visit_closed_dates`, `service_menus`.

- 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
- `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
- 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK).
- **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
- customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
- 같은 아이(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약은 하나다(부분 유일 색인 — 409 `VISIT_DUPLICATE`, 세이브포인트라 트랜잭션은 계속 쓴다).
- 겹침·휴무·영업시간 밖은 **막지 않는 경고**다. 판단은 `domain/services/visit_schedule.warnings_for` 한 곳에만 있다.
- "오늘"과 하루의 경계는 매장 시간대(`ShopContext.timezone`)로 센다. 요청 시각은 시간대가 붙어 와야 하고, 응답 시각은 매장 시간대로 나간다.
- 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각을 `CustomerDirectoryPort.set_last_visit`로 같은 트랜잭션에서 넘긴다(고객 목록 '최근 방문순'). 어긋나면 `scripts/rebuild_last_visit.py`로 복구한다.
- 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
