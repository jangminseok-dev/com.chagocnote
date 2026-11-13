"""확인할 것의 방문 쪽 사실 — 실제 PostgreSQL 에서 '이 방문 앞'의 경계와 노쇼 창의 양 끝을 본다(③-B)."""
from datetime import timedelta

import pytest

from visit.adapter.outbound.pg.visit_check_pg_repository import VisitCheckPgRepository
from visit.app.ports.output.visit_check_repository import HistoryAsk, NoShowAsk
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_마지막_완료_방문은_묻는_시각보다_앞에_시작한_것만이다(db_session):
    repo = VisitCheckPgRepository(db_session)
    old = kst(8, 1, 10)
    recent = kst(10, 20, 10)
    await insert_visit(db_session, old, status="completed")
    await insert_visit(db_session, recent, status="completed")
    await insert_visit(db_session, kst(11, 1, 10), status="canceled")       # 완료가 아니다
    await insert_visit(db_session, kst(11, 2, 10), status="no_show")
    await insert_visit(db_session, kst(11, 3, 10), status="in_progress")
    await insert_visit(db_session, kst(11, 20, 10), status="completed")      # 뒤의 방문
    await insert_visit(db_session, kst(10, 25, 10), status="completed", pet_id=102)   # 다른 아이
    await insert_visit(db_session, kst(10, 28, 10), status="completed", shop_id=2)    # 다른 매장

    found = await repo.last_completed(A, [
        HistoryAsk(key=1, pet_id=101, before=kst(11, 14, 10)),
        HistoryAsk(key=2, pet_id=101, before=recent),                 # 자기 자신은 세지 않는다(같은 시각은 '앞'이 아니다)
        HistoryAsk(key=3, pet_id=101, before=recent + timedelta(minutes=1)),
        HistoryAsk(key=4, pet_id=101, before=old),                    # 그 앞에는 없다
        HistoryAsk(key=5, pet_id=102, before=kst(11, 14, 10)),
        HistoryAsk(key=6, pet_id=999, before=kst(11, 14, 10)),        # 없는 아이
    ])

    assert found == {1: recent, 2: old, 3: recent, 4: None, 5: kst(10, 25, 10), 6: None}
    # 다른 매장의 컨텍스트로는 그 매장의 방문만 보인다.
    assert await repo.last_completed(B, [HistoryAsk(key=1, pet_id=101, before=kst(11, 14, 10))]) == {
        1: kst(10, 28, 10),
    }


async def test_노쇼는_창의_시작을_품고_끝을_품지_않는다(db_session):
    repo = VisitCheckPgRepository(db_session)
    since, until = kst(9, 1, 0), kst(11, 14, 10)
    await insert_visit(db_session, since, status="no_show")                               # 창의 첫 순간 — 센다
    await insert_visit(db_session, since - timedelta(minutes=10), status="no_show")       # 그 앞 — 안 센다
    await insert_visit(db_session, kst(10, 1, 10), status="no_show")
    await insert_visit(db_session, until, status="no_show")                               # 끝 — 안 센다
    await insert_visit(db_session, kst(10, 2, 10), status="completed")                    # 노쇼가 아니다
    await insert_visit(db_session, kst(10, 3, 10), status="no_show", customer_id=2, pet_id=201)
    await insert_visit(db_session, kst(10, 4, 10), status="no_show", pet_id=None)         # 보호자만의 방문도 센다
    await insert_visit(db_session, kst(10, 5, 10), status="no_show", shop_id=2)

    found = await repo.no_shows(A, [
        NoShowAsk(key=1, customer_id=1, since=since, until=until),
        NoShowAsk(key=2, customer_id=2, since=since, until=until),
        NoShowAsk(key=3, customer_id=3, since=since, until=until),                        # 노쇼가 없는 보호자
        NoShowAsk(key=4, customer_id=1, since=kst(10, 1, 10), until=kst(10, 1, 11)),      # 좁은 창
    ])

    assert found == {1: 3, 2: 1, 3: 0, 4: 1}
    assert await repo.no_shows(B, [NoShowAsk(key=1, customer_id=1, since=since, until=until)]) == {1: 1}


async def test_물음이_없으면_읽지_않는다(db_session):
    repo = VisitCheckPgRepository(db_session)
    assert await repo.last_completed(A, []) == {}
    assert await repo.no_shows(A, []) == {}
