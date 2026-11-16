"""⑬ 미용 주기 · 다시 올 때가 된 아이 · 결제 완료와 남은 일 · 하루 마무리 — 조립된 앱과 실제 DB."""
from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.integration.support import error_of
from tests.integration.test_sales_wiring import _day, _family, _move, _shop, _staff, _visit

pytestmark = pytest.mark.integration

DEFAULT_MESSAGE = "안녕하세요, {매장}예요.\n{아이}가 미용한 지 {주}주가 됐어요.\n편하신 날 알려 주시면 예약 잡아 드릴게요."


def settings_url(shop_id: int) -> str:
    return f"/v1/shops/{shop_id}/revisit-settings"


# ── 매장의 값(예약 설정) ─────────────────────────────────────────────


async def test_다시_올_때의_설정은_처음_값으로_보이고_보낸_칸만_바뀐다(wired):
    shop_id, o, _ = await _shop(wired)

    got = (await wired.api.get(settings_url(shop_id), headers=o)).json()
    assert got == {
        "default_cycle_weeks": 4, "revisit_soon_days": 7, "revisit_message": None, "count_unsent_reports": True,
        "cycle_sample_visits": 6, "cycle_min_gap_days": 7,
        "defaults": {"default_cycle_weeks": 4, "revisit_soon_days": 7, "revisit_message": DEFAULT_MESSAGE,
                     "count_unsent_reports": True, "cycle_sample_visits": 6, "cycle_min_gap_days": 7},
    }

    saved = await wired.api.put(settings_url(shop_id), headers=o, json={"revisit_soon_days": 10})
    assert saved.status_code == 200, saved.text
    assert (saved.json()["revisit_soon_days"], saved.json()["default_cycle_weeks"]) == (10, 4)

    await wired.api.put(settings_url(shop_id), headers=o,
                        json={"revisit_message": "{아이} 미용할 때가 됐어요", "cycle_min_gap_days": 0})
    kept = (await wired.api.get(settings_url(shop_id), headers=o)).json()
    assert (kept["revisit_soon_days"], kept["revisit_message"], kept["cycle_min_gap_days"]) == (
        10, "{아이} 미용할 때가 됐어요", 0)

    # null 은 처음 글로 돌아가기다.
    reset = await wired.api.put(settings_url(shop_id), headers=o, json={"revisit_message": None})
    assert reset.json()["revisit_message"] is None


@pytest.mark.parametrize("body", [
    {"default_cycle_weeks": 53}, {"revisit_soon_days": 0}, {"cycle_sample_visits": 2}, {"cycle_min_gap_days": 29},
    {"revisit_message": ""}, {"revisit_message": "가" * 301}, {"count_unsent_reports": "yes"},
])
async def test_범위_밖이나_빈_글은_422_이고_저장되지_않는다(wired, body):
    shop_id, o, _ = await _shop(wired)

    assert error_of(await wired.api.put(settings_url(shop_id), headers=o, json=body))[0] == 422
    assert (await wired.api.get(settings_url(shop_id), headers=o)).json()["default_cycle_weeks"] == 4


async def test_직원은_다시_올_때의_설정을_읽고_바꾸지_못한다(wired):
    shop_id, o, _ = await _shop(wired)
    staff = await _staff(wired, shop_id, o)

    assert (await wired.api.get(settings_url(shop_id), headers=staff)).status_code == 200
    assert error_of(await wired.api.put(settings_url(shop_id), headers=staff, json={"revisit_soon_days": 3}))[0] == 403


async def test_다른_매장의_설정은_볼_수_없다(wired):
    shop_id, o, operator = await _shop(wired)
    other_id, _, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)

    assert (await wired.api.get(settings_url(other_id), headers=o)).status_code in (403, 404)
    assert (await wired.api.put(settings_url(other_id), headers=o, json={"revisit_soon_days": 3})).status_code in (403, 404)
    assert (await wired.api.get(settings_url(shop_id), headers=o)).json()["revisit_soon_days"] == 7


# ── 아이의 주기 — 반려동물 상세, 직접 정하기, 안내한 날 ──────────────────


async def _done_on(wired, shop_id, headers, customer_id, pet_id, days, hour=11, record=None):
    """days 일 전(음수) 그 시각의 완료 방문."""
    visit_id = await _visit(wired, shop_id, headers, customer_id, pet_id, hour, days=days)
    await _move(wired, shop_id, headers, visit_id, "start")
    if record is not None:
        saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", json=record, headers=headers)
        assert saved.status_code == 200, saved.text
    await _move(wired, shop_id, headers, visit_id, "complete")
    return visit_id


async def _revisit(wired, shop_id, headers, pet_id):
    got = await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)
    assert got.status_code == 200, got.text
    return got.json()["revisit"]


def cycle_url(shop_id, pet_id):
    return f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-cycle"


async def test_반려동물_상세의_주기는_방문이_없으면_모르고_한_번이면_어림_간격_둘이면_계산이다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)

    none = await _revisit(wired, shop_id, o, pet_id)
    assert none == {"cycle_weeks": 4, "cycle_source": "none", "interval_count": 0, "last_interval_weeks": None,
                    "last_visit_date": None, "due_date": None, "estimated": True, "has_upcoming": False,
                    "nudged_on": None}

    await _done_on(wired, shop_id, o, customer_id, pet_id, -84)
    once = await _revisit(wired, shop_id, o, pet_id)
    assert (once["cycle_source"], once["cycle_weeks"], once["estimated"]) == ("none", 4, True)
    assert once["due_date"] == (_day(-84) + timedelta(weeks=4)).isoformat()

    await _done_on(wired, shop_id, o, customer_id, pet_id, -42)
    single = await _revisit(wired, shop_id, o, pet_id)
    assert (single["cycle_source"], single["last_interval_weeks"], single["cycle_weeks"]) == ("single", 6, 4)

    await _done_on(wired, shop_id, o, customer_id, pet_id, -1)
    computed = await _revisit(wired, shop_id, o, pet_id)
    assert (computed["cycle_source"], computed["interval_count"], computed["estimated"]) == ("computed", 2, False)
    assert computed["cycle_weeks"] == 6   # 간격 42·41일 → 41.5일 → 6주
    assert computed["last_visit_date"] == _day(-1).isoformat()
    assert computed["due_date"] == (_day(-1) + timedelta(weeks=6)).isoformat()


async def test_주기를_직접_정하면_앞서고_지우면_계산으로_돌아간다_직원도_정한다(wired):
    shop_id, o, _ = await _shop(wired)
    staff = await _staff(wired, shop_id, o)
    customer_id, pet_id = await _family(wired, shop_id, o)
    await _done_on(wired, shop_id, o, customer_id, pet_id, -10)

    put = await wired.api.put(cycle_url(shop_id, pet_id), headers=staff, json={"weeks": 8})
    assert put.status_code == 204, put.text
    manual = await _revisit(wired, shop_id, o, pet_id)
    assert (manual["cycle_source"], manual["cycle_weeks"], manual["estimated"]) == ("manual", 8, False)
    assert manual["due_date"] == (_day(-10) + timedelta(weeks=8)).isoformat()

    for weeks in (0, 53, "6"):
        assert error_of(await wired.api.put(cycle_url(shop_id, pet_id), headers=o, json={"weeks": weeks}))[0] == 422
    assert (await _revisit(wired, shop_id, o, pet_id))["cycle_weeks"] == 8

    assert (await wired.api.delete(cycle_url(shop_id, pet_id), headers=o)).status_code == 204
    assert (await _revisit(wired, shop_id, o, pet_id))["cycle_source"] == "none"


async def test_다른_매장의_아이의_주기는_정하지_못한다(wired):
    shop_id, o, operator = await _shop(wired)
    other_id, other, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)
    _, pet_id = await _family(wired, other_id, other)

    assert (await wired.api.put(cycle_url(shop_id, pet_id), headers=o, json={"weeks": 6})).status_code == 404
    assert (await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/revisit-nudge", headers=o)).status_code == 404
    assert (await _revisit(wired, other_id, other, pet_id))["cycle_source"] == "none"


async def test_안내한_날을_오늘로_적고_앞날_예약이_있으면_알린다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    await _done_on(wired, shop_id, o, customer_id, pet_id, -30)

    nudged = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/revisit-nudge", headers=o)
    assert nudged.status_code == 204, nudged.text
    got = await _revisit(wired, shop_id, o, pet_id)
    assert (got["nudged_on"], got["has_upcoming"]) == (_day(0).isoformat(), False)

    await _visit(wired, shop_id, o, customer_id, pet_id, 11, days=3)
    assert (await _revisit(wired, shop_id, o, pet_id))["has_upcoming"] is True


async def test_익명화하면_아이의_주기와_안내한_날이_비워진다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    await wired.api.put(cycle_url(shop_id, pet_id), headers=o, json={"weeks": 6})
    await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/revisit-nudge", headers=o)

    async def row():
        async with wired.engine.connect() as conn:
            return tuple((await conn.execute(text(
                "SELECT grooming_cycle_weeks, revisit_nudged_on FROM pets WHERE id = :id"), {"id": pet_id})).one())

    assert await row() == (6, _day(0))
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204
    assert await row() == (None, None)


# ── 다음 예약 초안 ─────────────────────────────────────────────────


async def _draft(wired, shop_id, headers, visit_id):
    got = await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}/next-draft", headers=headers)
    assert got.status_code == 200, got.text
    return got.json()


async def test_다음_예약_초안은_날짜가_늘_있고_주기의_출처를_싣는다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)

    once = await _done_on(wired, shop_id, o, customer_id, pet_id, -84)
    first = await _draft(wired, shop_id, o, once)
    assert (first["cycle_source"], first["cycle_weeks"], first["interval_weeks"]) == ("none", 4, 4)
    assert first["starts_at"].startswith((_day(-84) + timedelta(weeks=4)).isoformat())

    await _done_on(wired, shop_id, o, customer_id, pet_id, -42)
    last = await _done_on(wired, shop_id, o, customer_id, pet_id, -1)
    computed = await _draft(wired, shop_id, o, last)
    assert (computed["cycle_source"], computed["cycle_weeks"]) == ("computed", 6)
    assert computed["starts_at"].startswith((_day(-1) + timedelta(weeks=6)).isoformat())

    await wired.api.put(cycle_url(shop_id, pet_id), headers=o, json={"weeks": 3})
    assert (await _draft(wired, shop_id, o, last))["cycle_source"] == "manual"

    # 매장의 기본 간격을 바꾸면 주기를 모르는 아이(한 번 온 아이)의 초안이 따라간다.
    new_customer, new_pet = await _family(wired, shop_id, o, phone="010-2222-3333", pet_name="보리")
    single = await _done_on(wired, shop_id, o, new_customer, new_pet, -3)
    await wired.api.put(settings_url(shop_id), headers=o, json={"default_cycle_weeks": 8})
    eight = await _draft(wired, shop_id, o, single)
    assert (eight["cycle_source"], eight["cycle_weeks"]) == ("none", 8)


# ── 다시 올 때가 된 아이 — 목록과 수 ─────────────────────────────────


async def _list(wired, shop_id, headers, bucket):
    got = await wired.api.get(f"/v1/shops/{shop_id}/revisits", params={"bucket": bucket}, headers=headers)
    assert got.status_code == 200, got.text
    return got.json()


async def _counts(wired, shop_id, headers):
    got = await wired.api.get(f"/v1/shops/{shop_id}/revisits/counts", headers=headers)
    assert got.status_code == 200, got.text
    return got.json()


async def test_다시_올_때가_된_아이는_곧과_지남으로_나뉘고_수와_목록이_같고_직원도_본다(wired):
    shop_id, o, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, o)
    other_id, other, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)

    kong_c, kong = await _family(wired, shop_id, o, phone="010-1111-0001", pet_name="콩이")
    for d in (-134, -92, -50):                          # 6주 주기 — 8일 지남
        await _done_on(wired, shop_id, o, kong_c, kong, d)
    bori_c, bori = await _family(wired, shop_id, o, phone="010-1111-0002", pet_name="보리")
    for d in (-81, -53, -25):                           # 4주 주기 — 3일 뒤
        await _done_on(wired, shop_id, o, bori_c, bori, d)
    two_c, two = await _family(wired, shop_id, o, phone="010-1111-0003", pet_name="두부")
    for d in (-29, -15):                                # 2주 간격 하나 — 15일째에도 어디에도 없다
        await _done_on(wired, shop_id, o, two_c, two, d)
    lost_c, lost = await _family(wired, other_id, other, phone="010-1111-0004", pet_name="남의아이")
    await _done_on(wired, other_id, other, lost_c, lost, -60)

    due = await _list(wired, shop_id, staff, "due")
    soon = await _list(wired, shop_id, staff, "soon")
    assert [(i["pet"]["name"], i["cycle_source"], i["due_date"]) for i in due["items"]] == [
        ("콩이", "computed", _day(-8).isoformat())]
    assert [(i["pet"]["name"], i["cycle_weeks"]) for i in soon["items"]] == [("보리", 4)]
    assert set(due["items"][0]) == {
        "pet", "last_visit_date", "last_visit_id", "cycle_weeks", "cycle_source", "last_interval_weeks",
        "due_date", "estimated", "nudged_on", "message"}
    assert due["items"][0]["message"].startswith("안녕하세요, Hiss Haus예요.\n콩이가 미용한 지 7주가 됐어요.")
    assert await _counts(wired, shop_id, staff) == {"soon": 1, "due": 1}

    # 예약을 잡으면 빠진다. 매출 요약의 지난 아이 수는 지남의 수다.
    await _visit(wired, shop_id, o, kong_c, kong, 11, days=5)
    assert (await _counts(wired, shop_id, o))["due"] == 0
    summary = (await wired.api.get(f"/v1/shops/{shop_id}/sales/summary", params={"span": "day"}, headers=o)).json()
    assert summary["due_pet_count"] == 0

    # 안내한 날은 마지막 방문 뒤에만 실린다.
    await wired.api.put(f"/v1/shops/{shop_id}/pets/{bori}/revisit-nudge", headers=o)
    assert (await _list(wired, shop_id, o, "soon"))["items"][0]["nudged_on"] == _day(0).isoformat()


async def test_묶음은_soon_과_due_만이고_깨진_커서는_422_다(wired):
    shop_id, o, _ = await _shop(wired)
    bad = await wired.api.get(f"/v1/shops/{shop_id}/revisits", params={"bucket": "later"}, headers=o)
    assert bad.status_code == 422
    broken = await wired.api.get(f"/v1/shops/{shop_id}/revisits", params={"bucket": "due", "cursor": "깨짐"},
                                 headers=o)
    assert error_of(broken)[0] == 422


async def test_예전_매출의_지난_아이_경로는_없다(wired):
    shop_id, o, _ = await _shop(wired)
    assert (await wired.api.get(f"/v1/shops/{shop_id}/sales/due-pets", headers=o)).status_code == 404


# ── 결제 완료와 남은 일 — 하루·달력·피드·방문 상세, 알림장 넘기기 ─────────────


async def _day_view(wired, shop_id, headers, days=-1):
    got = await wired.api.get(f"/v1/shops/{shop_id}/visits", params={"date": _day(days).isoformat()}, headers=headers)
    assert got.status_code == 200, got.text
    return got.json()


async def _calendar_day(wired, shop_id, headers, days=-1):
    day = _day(days)
    got = await wired.api.get(f"/v1/shops/{shop_id}/visits/calendar", params={"month": day.strftime("%Y-%m")},
                              headers=headers)
    assert got.status_code == 200, got.text
    return next(d for d in got.json()["days"] if d["date"] == day.isoformat())


async def _record(wired, shop_id, headers, visit_id, **body):
    """기록 전체 교체 — 있던 기록의 버전을 읽어 보낸다."""
    found = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=headers)).json()["record"]
    version = {"version": found["version"]} if found else {}
    saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                json={"care_note": "잘 참았어요.", **version, **body})
    assert saved.status_code == 200, saved.text


async def test_총액과_결제_수단을_적으면_결제_완료이고_하루의_결제_안_적음에서_빠진다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    visit_id = await _done_on(wired, shop_id, o, customer_id, pet_id, -1, record={"total_amount": 30_000})

    day = await _day_view(wired, shop_id, o)
    [item] = day["items"]
    assert (item["marks"], day["counts"]["unpaid"]) == ([], 1)
    assert (await _calendar_day(wired, shop_id, o))["unpaid_count"] == 1

    await _record(wired, shop_id, o, visit_id, total_amount=30_000, payment_method="card")
    day = await _day_view(wired, shop_id, o)
    assert (day["items"][0]["marks"], day["counts"]["unpaid"]) == (["paid"], 0)
    assert (await _calendar_day(wired, shop_id, o))["unpaid_count"] == 0
    feed = (await wired.api.get(f"/v1/shops/{shop_id}/visits/feed", headers=o)).json()
    assert feed["items"][0]["marks"] == ["paid"]
    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=o)).json()
    assert (detail["marks"], detail["report_skipped"]) == (["paid"], False)


async def test_알림장_안_보냄은_줄이_한_번도_없는_방문이고_넘기면_빠지고_보냈다_끊어도_다시_세지_않는다(wired):
    shop_id, o, _ = await _shop(wired)
    staff = await _staff(wired, shop_id, o)
    customer_id, pet_id = await _family(wired, shop_id, o)
    visit_id = await _done_on(wired, shop_id, o, customer_id, pet_id, -1,
                              record={"care_note": "잘 참았어요.", "total_amount": 0})
    skip = f"/v1/shops/{shop_id}/visits/{visit_id}/report-skip"

    assert (await _day_view(wired, shop_id, o))["counts"]["report_unsent"] == 1
    assert (await _calendar_day(wired, shop_id, o))["report_unsent_count"] == 1

    assert (await wired.api.put(skip, headers=staff)).status_code == 204
    assert (await _day_view(wired, shop_id, o))["counts"]["report_unsent"] == 0
    assert (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=o)).json()["report_skipped"] is True
    assert (await wired.api.delete(skip, headers=o)).status_code == 204
    assert (await _day_view(wired, shop_id, o))["counts"]["report_unsent"] == 1

    # 매장이 세지 않기로 하면 하루와 달력에서 세지 않는다.
    await wired.api.put(settings_url(shop_id), headers=o, json={"count_unsent_reports": False})
    assert (await _day_view(wired, shop_id, o))["counts"]["report_unsent"] == 0
    assert (await _calendar_day(wired, shop_id, o))["report_unsent_count"] == 0
    await wired.api.put(settings_url(shop_id), headers=o, json={"count_unsent_reports": True})

    sent = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/report", headers=o,
                               json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    day = await _day_view(wired, shop_id, o)
    assert (day["counts"]["report_unsent"], day["items"][0]["marks"]) == (0, ["paid", "report_sent"])
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/visits/{visit_id}/report", headers=o)).status_code == 204
    day = await _day_view(wired, shop_id, o)
    assert (day["counts"]["report_unsent"], day["items"][0]["marks"]) == (0, ["paid"])   # 보낸 적이 있다


async def test_알림장_넘기기는_완료이고_기록이_있는_방문만이고_남의_방문은_404다(wired):
    shop_id, o, operator = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    reserved = await _visit(wired, shop_id, o, customer_id, pet_id, 11, days=2)
    bare = await _done_on(wired, shop_id, o, customer_id, pet_id, -1)
    assert error_of(await wired.api.put(f"/v1/shops/{shop_id}/visits/{reserved}/report-skip", headers=o))[0] == 409
    assert error_of(await wired.api.put(f"/v1/shops/{shop_id}/visits/{bare}/report-skip", headers=o))[0] == 409
    other_id, other, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)
    assert (await wired.api.put(f"/v1/shops/{other_id}/visits/{bare}/report-skip", headers=other)).status_code == 404


async def test_앞날에는_남은_일이_없고_하루의_수에_확인할_것이_든다_금액은_없다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    await _visit(wired, shop_id, o, customer_id, pet_id, 11, days=3)      # 처음 오는 아이 — 확인할 것(첫 방문)
    ahead = await _day_view(wired, shop_id, o, days=3)
    assert (ahead["counts"]["unpaid"], ahead["counts"]["report_unsent"], ahead["counts"]["checks"]) == (0, 0, 1)
    day = await _calendar_day(wired, shop_id, o, days=3)
    assert (day["unpaid_count"], day["report_unsent_count"]) == (0, 0)
    assert not any("amount" in key for key in ahead["counts"]) and not any("amount" in key for key in day)
