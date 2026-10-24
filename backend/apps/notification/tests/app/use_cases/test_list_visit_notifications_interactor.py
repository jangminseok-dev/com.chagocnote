"""방문별 발송 내역 — 최신순, 실패 줄에만 share_text(문자용 문안). 익명화된 고객이면 null. 다른 매장의 방문은 빈 목록."""
from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT, REPORT
from notification.domain.value_objects.message_status import CANCELED, FAILED, SCHEDULED, SENT
from notification.tests.helpers.builders import ctx, kst, message
from notification.tests.helpers.message_world import MessageWorld

STARTS = kst(10, 16, 14)       # 16일(금) 14:00
URL = "https://a/" + "t" * 43
VARIABLES = {"starts_at": STARTS.isoformat()}


def _query(visit_id=1, shop_id=1) -> ListVisitNotificationsQuery:
    return ListVisitNotificationsQuery(ctx=ctx(shop_id=shop_id), visit_id=visit_id)


async def test_최신순이고_실패_줄에만_share_text_가_있다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=SENT, created_at=kst(10, 14, 11), variables=VARIABLES)
    world.messages.rows[2] = message(id=2, status=FAILED, error_kind="permanent", created_at=kst(10, 14, 12),
                                     variables=VARIABLES, pet_id=101)
    world.messages.rows[3] = message(id=3, status=CANCELED, canceled_reason="setting_off", created_at=kst(10, 14, 12),
                                     variables=VARIABLES)
    world.messages.rows[4] = message(id=4, status=SCHEDULED, created_at=kst(10, 14, 10), variables=VARIABLES)
    world.messages.rows[5] = message(id=5, visit_id=2, status=FAILED, created_at=kst(10, 14, 13), variables=VARIABLES)

    views = await world.list.list_visit_notifications(_query())

    assert [(v.message.id, v.share_text) for v in views] == [
        (3, None), (2, "[두부네] 10월 16일(금) 14:00 예약이 접수되었어요."), (1, None), (4, None)]


async def test_대상은_반려동물_이름이고_없으면_보호자_이름에_님이다():
    world = MessageWorld()
    variables = {**VARIABLES, "completed_at": kst(9, 16, 14).isoformat(), "interval_weeks": "4"}
    world.messages.rows[1] = message(id=1, kind=NEXT_VISIT, status=FAILED, pet_id=101, variables=variables)
    world.messages.rows[2] = message(id=2, kind=NEXT_VISIT, status=FAILED, pet_id=None, variables=variables,
                                     created_at=kst(10, 14, 12))

    views = await world.list.list_visit_notifications(_query())

    assert [v.share_text for v in views] == ["[두부네] 김민지님 미용한 지 4주가 지났어요.", "[두부네] 콩이 미용한 지 4주가 지났어요."]


async def test_알림장의_share_text_에는_주소가_든다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, kind=REPORT, status=FAILED, pet_id=101,
                                     variables={**VARIABLES, "url": URL, "expires_at": ""})

    [view] = await world.list.list_visit_notifications(_query())

    assert view.share_text == f"[두부네] 알림장 {URL}"


async def test_익명화된_고객의_실패_줄은_share_text_가_없다():
    world = MessageWorld()
    world.directory.contacts.pop(1)
    world.messages.rows[1] = message(id=1, kind=CONFIRM, status=FAILED, variables=VARIABLES)

    [view] = await world.list.list_visit_notifications(_query())

    assert view.message.status == FAILED and view.share_text is None


async def test_다른_매장의_방문이거나_없는_방문이면_빈_목록이다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=FAILED, variables=VARIABLES)

    assert await world.list.list_visit_notifications(_query(visit_id=1, shop_id=2)) == []
    assert await world.list.list_visit_notifications(_query(visit_id=9)) == []
