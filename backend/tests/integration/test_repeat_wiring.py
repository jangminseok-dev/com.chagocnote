"""반복 예약(⑭-1)을 실제 배선으로 확인한다 — 한 묶음으로 잡기, 알림 줄은 접수 한 통·리마인드 회차마다, `이후 전부`
옮기기(주마다 묶음을 1주 밀기 포함)·걸린 회차·빼고 다시·취소, 방문 상세의 자리와 묶음 목록, 방문마다 검색 줄."""
import pytest
from sqlalchemy import text

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import add_pet
from tests.integration.test_notification_subscriber_wiring import _link
from tests.integration.test_visit_checks_wiring import _at, _family, _pet, _shop

pytestmark = pytest.mark.integration


async def _rows(wired, sql: str, **params) -> list:
    async with wired.engine.connect() as conn:
        return list(await conn.execute(text(sql), params))


async def _series(wired, shop_id, headers, customer_id, pet_ids, interval=1, count=6, first=_at(2, 14)):
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": pet_ids, "starts_at": first,
        "repeat": {"interval_weeks": interval, "count": count}})
    assert booked.status_code == 201, booked.text
    return booked.json()


async def _starts(wired, ids) -> list:
    rows = await _rows(wired, "SELECT id, starts_at, status FROM visits WHERE id = ANY(:ids) ORDER BY starts_at, id",
                       ids=list(ids))
    return [(r.id, r.starts_at, r.status) for r in rows]


async def _kinds(wired, customer_id) -> dict[str, int]:
    rows = await _rows(wired, "SELECT m.kind, count(*) AS n FROM notification_messages m JOIN visits v "
                              "ON v.id = m.visit_id WHERE v.customer_id = :c AND m.status = 'scheduled' "
                              "GROUP BY m.kind", c=customer_id)
    return {r.kind: r.n for r in rows}


async def test_다른_매장의_미리_보기는_403(wired):
    shop_id, headers, operator = await _shop(wired)
    other_id, _, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)
    response = await wired.api.get(
        f"/v1/shops/{other_id}/visits/repeat-preview?customer_id=1&interval_weeks=4&count=2"
        f"&starts_at={_at(1, 14).replace('+', '%2B')}", headers=headers)
    assert response.status_code == 403


async def test_가족_6회_반복은_한_묶음이고_알림은_접수_한_통_리마인드_여섯(wired):
    shop_id, headers, _ = await _shop(wired)
    await _link(wired, shop_id)
    customer_id, kong = await _family(wired, shop_id, headers, _pet())
    dubu = await add_pet(wired, shop_id, headers, customer_id, _pet(name="두부"))
    await wired.execute("DELETE FROM search_jobs")
    body = await _series(wired, shop_id, headers, customer_id, [kong, dubu])

    ids = [v["visit_id"] for v in body["visits"]]
    assert len(ids) == 12 and len(body["series"]["occurrences"]) == 6
    series = await _rows(wired, "SELECT DISTINCT series_id FROM visits WHERE id = ANY(:ids)", ids=ids)
    assert [r.series_id for r in series] == [body["series"]["id"]]
    assert await _kinds(wired, customer_id) == {"confirm": 1, "reminder": 6}
    jobs = await _rows(wired, "SELECT ref_id FROM search_jobs WHERE scope = 'visit'")
    assert sorted(r.ref_id for r in jobs) == sorted(ids)


async def test_주마다_묶음을_이후_전부로_1주_밀어도_된다(wired):
    shop_id, headers, _ = await _shop(wired)
    await _link(wired, shop_id)
    customer_id, kong = await _family(wired, shop_id, headers, _pet())
    ids = [v["visit_id"] for v in (await _series(wired, shop_id, headers, customer_id, [kong], count=4))["visits"]]
    before = await _starts(wired, ids)

    moved = await wired.api.post(f"/v1/shops/{shop_id}/visits/reschedule", headers=headers, json={
        "visit_ids": [ids[1]], "starts_at": _at(16, 14), "scope": "following"})
    assert moved.status_code == 200, moved.text
    after = {vid: at for vid, at, _ in await _starts(wired, ids)}
    assert after[ids[0]] == before[0][1]
    assert [after[i] for i in ids[1:]] == [before[2][1], before[3][1], before[3][1] + (before[3][1] - before[2][1])]
    assert [p["kind"] for p in moved.json()["notice"]] == ["series_change"]
    assert (await _kinds(wired, customer_id))["change"] == 1


async def test_걸린_회차가_있으면_409_details_와_아무것도_바뀌지_않음_빼고_다시_보내면_된다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet())
    ids = [v["visit_id"] for v in (await _series(wired, shop_id, headers, customer_id, [kong], count=3))["visits"]]
    outside = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [kong], "starts_at": _at(16, 15)})
    assert outside.status_code == 201
    before = await _starts(wired, ids)

    payload = {"visit_ids": [ids[1]], "starts_at": _at(9, 15), "scope": "following"}
    conflict = await wired.api.post(f"/v1/shops/{shop_id}/visits/reschedule", headers=headers, json=payload)
    assert error_of(conflict) == (409, "VISIT_SERIES_CONFLICT")
    [hit] = conflict.json()["details"]["conflicts"]
    assert (hit["visit_id"], hit["reason"]) == (ids[2], "taken")
    assert await _starts(wired, ids) == before

    again = await wired.api.post(f"/v1/shops/{shop_id}/visits/reschedule", headers=headers,
                                 json={**payload, "skip_visit_ids": [ids[2]]})
    assert again.status_code == 200, again.text
    after = {vid: at for vid, at, _ in await _starts(wired, ids)}
    assert after[ids[2]] == before[2][1] and after[ids[1]] != before[1][1]


async def test_이후_전부_취소는_뒤의_예약됨만이고_취소_안내_한_통(wired):
    shop_id, headers, _ = await _shop(wired)
    await _link(wired, shop_id)
    customer_id, kong = await _family(wired, shop_id, headers, _pet())
    ids = [v["visit_id"] for v in (await _series(wired, shop_id, headers, customer_id, [kong], count=4))["visits"]]
    alone = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers, json={
        "visit_ids": [ids[2]], "action": "cancel", "cancel_reason": "customer_request"})
    assert alone.status_code == 200

    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers, json={
        "visit_ids": [ids[1]], "action": "cancel", "cancel_reason": "shop_reason", "scope": "following"})
    assert response.status_code == 200, response.text
    assert sorted(v["visit_id"] for v in response.json()["visits"]) == [ids[1], ids[3]]
    assert [status for _, _, status in await _starts(wired, ids)] == ["reserved", "canceled", "canceled", "canceled"]
    [part] = response.json()["notice"]
    assert part["kind"] == "series_cancel" and part["text"].count("\n· ") == 2
    assert (await _kinds(wired, customer_id)).get("cancel") == 1


async def test_방문_상세의_묶음_자리와_묶음_목록(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet())
    body = await _series(wired, shop_id, headers, customer_id, [kong], interval=4, count=3)
    ids = [v["visit_id"] for v in body["visits"]]

    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{ids[1]}", headers=headers)).json()
    assert detail["series"] == {"id": body["series"]["id"], "interval_weeks": 4, "position": 2, "total": 3,
                                "is_last": False}
    listed = await wired.api.get(f"/v1/shops/{shop_id}/visit-series/{body['series']['id']}", headers=headers)
    assert [v["visit_id"] for v in listed.json()["visits"]] == ids
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/visit-series/999999", headers=headers)) == (
        404, "VISIT_SERIES_NOT_FOUND")
