"""보호자의 기록 모아 보기(⑫ 설계 3.3·3.4) — 아이의 사진·영상을 날짜를 넘어, 몸무게 변화.

같음 테스트: 보호자가 볼 수 있는 한 장들의 미디어 = 모아 보기를 끝까지 넘긴 미디어(끊기·뺀 미디어·다시 보내기·
보호자만의 방문을 섞어서). 서명 주소의 질의 문자열은 떼고 견준다(서명은 그때마다 다르다).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import error_of, ready_photo
from tests.integration.test_guardian_wiring import claim, web_login
from tests.integration.test_public_report_wiring import ALL_ON, CUSTOMER, PET, _shop, _token

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
LINKS = "/v1/me/guardian/links"


def _key(url: str) -> str:
    return url.split("?", 1)[0]


async def _family(wired, shop_id, headers):
    made = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                json={"customer": CUSTOMER, "pet": PET})
    assert made.status_code == 201, made.text
    customer_id = made.json()["customer"]["customer_id"]
    second = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers,
                                  json={**PET, "name": "두부"})
    assert second.status_code == 201, second.text
    return customer_id, made.json()["pets"][0]["pet_id"], second.json()["pet"]["pet_id"]


async def _visit(wired, shop_id, headers, customer_id, pet_id, days_ago, *, photos=0, weight=None, before=0):
    """days_ago 날의 완료 방문(후 사진 photos 장, 전 사진 before 장, 몸무게). (방문 주소, 후 미디어, 전 미디어)."""
    day = datetime.now(SEOUL).date() - timedelta(days=days_ago)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [pet_id] if pet_id else [],
        "starts_at": datetime(day.year, day.month, day.day, 11, tzinfo=SEOUL).isoformat()})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
    after = [await ready_photo(wired, shop_id, headers) for _ in range(photos)]
    before_ids = [await ready_photo(wired, shop_id, headers) for _ in range(before)]
    media = [{"media_id": m, "phase": "after", "sort_order": i} for i, m in enumerate(after)]
    media += [{"media_id": m, "phase": "before", "sort_order": i} for i, m in enumerate(before_ids)]
    for action in ("start", "record", "complete"):
        if action == "record":
            done = await wired.api.put(f"{visit}/record", headers=headers, json={"weight_kg": weight, "media": media})
        else:
            done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                        json={"visit_ids": [visit_id], "action": action})
        assert done.status_code == 200, done.text
    return visit, after, before_ids


async def _send(wired, visit, headers, hidden=()):
    sent = await wired.api.put(f"{visit}/report", headers=headers, json={"hidden_media_ids": list(hidden)})
    assert sent.status_code == 200, sent.text
    return _token(sent.json()["link"])


async def _all_media(wired, guardian, link_id, **params):
    """모아 보기를 끝 쪽까지 넘긴다."""
    seen, cursor = [], None
    while True:
        query = {k: v for k, v in {**params, "cursor": cursor}.items() if v is not None}
        page = await wired.api.get(f"{LINKS}/{link_id}/media", headers=guardian, params=query)
        assert page.status_code == 200, page.text
        seen += page.json()["items"]
        cursor = page.json()["next_cursor"]
        if cursor is None:
            return seen


async def _world(wired):
    """끊기·뺀 미디어·보호자만의 방문을 섞은 한 가족. (보호자, link_id, 매장, 헤더, 아이들, 방문들)."""
    shop_id, o = await _shop(wired)
    await wired.api.put(f"/v1/shops/{shop_id}/report-settings", headers=o, json={**ALL_ON, "show_weight": True})
    customer_id, kong, dubu = await _family(wired, shop_id, o)
    old, old_after, _ = await _visit(wired, shop_id, o, customer_id, kong, 360, photos=2, weight=3.0)
    mid, mid_after, mid_before = await _visit(wired, shop_id, o, customer_id, kong, 30, photos=2, before=1, weight=3.2)
    cut, _, _ = await _visit(wired, shop_id, o, customer_id, kong, 20, photos=1, weight=9.9)
    other, other_after, _ = await _visit(wired, shop_id, o, customer_id, dubu, 10, photos=1)
    owner_only, owner_after, _ = await _visit(wired, shop_id, o, customer_id, None, 5, photos=1)
    token = await _send(wired, old, o)
    await _send(wired, mid, o, hidden=[mid_after[1]])                 # 하나는 알림장에서 뺐다
    await _send(wired, cut, o)
    assert (await wired.api.delete(f"{cut}/report", headers=o)).status_code == 204   # 끊었다
    await _send(wired, other, o)
    await _send(wired, owner_only, o)
    guardian = await web_login(wired, "모아보는보호자")
    link_id = (await claim(wired, guardian, token)).json()["link_id"]
    return guardian, link_id, shop_id, o, (kong, dubu), dict(old=old_after, mid=mid_after, mid_before=mid_before,
                                                             other=other_after, owner=owner_after)


async def test_모아_보기의_미디어는_보호자가_볼_수_있는_한_장들의_미디어와_같다(wired, media_storage):
    guardian, link_id, _, _, _, _ = await _world(wired)
    pages = (await wired.api.get(f"{LINKS}/{link_id}/reports", headers=guardian)).json()["items"]
    from_reports = set()
    for item in pages:
        one = (await wired.api.get(f"{LINKS}/{link_id}/reports/{item['report_id']}", headers=guardian)).json()
        from_reports |= {_key(m["download_url"]) for m in one["media"]}

    archive = await _all_media(wired, guardian, link_id)

    assert {_key(m["download_url"]) for m in archive} == from_reports and len(archive) == len(from_reports) == 6
    first = archive[0]
    assert set(first) == {"report_id", "visit_date", "kind", "phase", "width", "height", "duration_seconds",
                          "display_url", "thumb_url", "download_url"}


async def test_최신순이고_한_방문_안에서는_후_다음_전이다(wired, media_storage):
    guardian, link_id, _, _, (kong, _), _ = await _world(wired)

    archive = await _all_media(wired, guardian, link_id, pet_id=kong)

    assert [m["visit_date"] for m in archive] == sorted((m["visit_date"] for m in archive), reverse=True)
    mid = [m["phase"] for m in archive if m["visit_date"] == archive[0]["visit_date"]]
    assert mid == ["after", "before"]                              # 30일 전 방문 — 뺀 후 사진 하나는 없다
    assert len(archive) == 4                                        # 콩이: 30일 전 2 + 360일 전 2


async def test_아이_연도_전후로_거르고_years_는_받은_알림장이_있는_해다(wired, media_storage):
    guardian, link_id, _, _, (kong, dubu), _ = await _world(wired)
    this_year = datetime.now(SEOUL).year

    page = (await wired.api.get(f"{LINKS}/{link_id}/media", headers=guardian, params={"pet_id": kong})).json()
    assert page["years"] == sorted({int(m["visit_date"][:4]) for m in await _all_media(wired, guardian, link_id, pet_id=kong)}, reverse=True)
    assert len(await _all_media(wired, guardian, link_id, pet_id=dubu)) == 1
    assert {m["phase"] for m in await _all_media(wired, guardian, link_id, phase="before")} == {"before"}
    old_year = (datetime.now(SEOUL).date() - timedelta(days=360)).year
    assert all(m["visit_date"].startswith(str(old_year)) for m in await _all_media(wired, guardian, link_id, year=old_year))
    assert this_year in page["years"]


async def test_한_쪽은_60개이고_다음_쪽으로_이어지며_깨진_커서는_422(wired, media_storage):
    shop_id, o = await _shop(wired)
    customer_id, kong, _ = await _family(wired, shop_id, o)
    tokens = []
    for days in range(3):
        visit, _, _ = await _visit(wired, shop_id, o, customer_id, kong, days + 1, photos=25)
        tokens.append(await _send(wired, visit, o))
    guardian = await web_login(wired, "많은사진보호자")
    link_id = (await claim(wired, guardian, tokens[0])).json()["link_id"]

    first = (await wired.api.get(f"{LINKS}/{link_id}/media", headers=guardian)).json()
    assert len(first["items"]) == 60 and first["next_cursor"] is not None
    rest = (await wired.api.get(f"{LINKS}/{link_id}/media", headers=guardian, params={"cursor": first["next_cursor"]})).json()
    assert len(rest["items"]) == 15 and rest["next_cursor"] is None
    assert not {_key(m["download_url"]) for m in first["items"]} & {_key(m["download_url"]) for m in rest["items"]}
    assert error_of(await wired.api.get(f"{LINKS}/{link_id}/media", headers=guardian, params={"cursor": "깨짐"}))[0] == 422
    assert error_of(await wired.api.get(f"{LINKS}/{link_id}/media", headers=guardian, params={"phase": "middle"}))[0] == 422


async def test_몸무게는_볼_수_있는_알림장의_것만_오래된_것부터이고_매장이_끄면_없다(wired, media_storage):
    guardian, link_id, shop_id, o, (kong, dubu), _ = await _world(wired)

    weights = (await wired.api.get(f"{LINKS}/{link_id}/pets/{kong}/weights", headers=guardian)).json()["items"]
    assert [w["weight_kg"] for w in weights] == [3.0, 3.2]          # 끊은 알림장의 9.9 는 없다
    assert weights[0]["visit_date"] < weights[1]["visit_date"]
    assert (await wired.api.get(f"{LINKS}/{link_id}/pets/{dubu}/weights", headers=guardian)).json()["items"] == []

    await wired.api.put(f"/v1/shops/{shop_id}/report-settings", headers=o, json={**ALL_ON, "show_weight": False})
    assert (await wired.api.get(f"{LINKS}/{link_id}/pets/{kong}/weights", headers=guardian)).json()["items"] == []


async def test_받은_적_없는_아이와_남의_연결은_404_다(wired, media_storage):
    guardian, link_id, _, _, _, _ = await _world(wired)
    stranger = await web_login(wired, "남")

    assert error_of(await wired.api.get(f"{LINKS}/{link_id}/pets/999999/weights", headers=guardian))[0] == 404
    assert error_of(await wired.api.get(f"{LINKS}/{link_id}/media", headers=stranger)) == (404, "GUARDIAN_LINK_NOT_FOUND")


async def test_다시_보내며_기간이_지나_닫힌_알림장은_모아_보기에서도_빠진다(wired, media_storage):
    guardian, link_id, shop_id, o, (kong, _), _ = await _world(wired)
    before = len(await _all_media(wired, guardian, link_id))
    async with wired.engine.begin() as conn:                       # 360일 전 방문의 링크 기간이 지났다
        await conn.execute(text(
            "UPDATE visit_reports SET expires_at = now() - interval '1 day', created_at = now() - interval '2 days' "
            "WHERE revoked_at IS NULL AND visit_id = (SELECT min(id) FROM visits WHERE shop_id = :shop)"), {"shop": shop_id})
    assert len(await _all_media(wired, guardian, link_id)) == before   # 기간만 지난 것은 로그인한 보호자에게 보인다

    async with wired.engine.connect() as conn:
        visit_id = (await conn.execute(text("SELECT min(id) FROM visits WHERE shop_id = :shop"), {"shop": shop_id})).scalar()
    await _send(wired, f"/v1/shops/{shop_id}/visits/{visit_id}", o)   # 다시 보내면 옛 줄은 닫히고 새 줄이 생긴다
    assert len(await _all_media(wired, guardian, link_id)) == before   # 새 줄로 같은 미디어가 보인다 — 겹치지 않는다


async def test_가족_연결도_같은_것을_본다(wired, media_storage):
    guardian, link_id, _, _, (kong, _), _ = await _world(wired)
    code = (await wired.api.post(f"{LINKS}/{link_id}/family-invites", headers=guardian)).json()["code"]
    family = await web_login(wired, "가족")
    family_link = (await wired.api.post("/v1/me/guardian/family-links", headers={**family, "X-Family-Invite": code})).json()["link_id"]

    mine = {_key(m["download_url"]) for m in await _all_media(wired, guardian, link_id)}
    theirs = {_key(m["download_url"]) for m in await _all_media(wired, family, family_link)}
    assert mine == theirs
    assert (await wired.api.get(f"{LINKS}/{family_link}/pets/{kong}/weights", headers=family)).json()["items"]
