"""알림장을 실제 배선(프로바이더·허브 포트 조립·설정 상수·DB·MinIO)으로 확인한다."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    ready_photo,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
NO_LINK = {"status": "none", "url": None, "expires_at": None, "first_viewed_at": None, "created_at": None,
           "show_review": None}
YESTERDAY = datetime.now(SEOUL).date() - timedelta(days=1)


async def _shop(wired, operator, name, owner_name):
    shop_id, owner = await shop_with_owner(wired, operator, name, owner_name)
    return shop_id, owner, bearer(owner["access_token"])


async def _started_visit(wired, shop_id, headers) -> int:
    """어제 11시에 시작한 콩이의 방문(어제라 자정을 넘기지 않는다 — 시각과 상관없이 돈다)."""
    family = await wired.api.post(f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET},
                                  headers=headers)
    assert family.status_code == 201, family.text
    starts_at = datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 11, tzinfo=SEOUL).isoformat()
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": family.json()["customer"]["customer_id"],
              "pet_ids": [family.json()["pets"][0]["pet_id"]], "starts_at": starts_at})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    started = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                   json={"visit_ids": [visit_id], "action": "start"})
    assert started.status_code == 200, started.text
    return visit_id


async def _complete(wired, shop_id, headers, visit_id) -> None:
    done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                json={"visit_ids": [visit_id], "action": "complete"})
    assert done.status_code == 200, done.text


async def _completed_visit(wired, shop_id, headers, photos=0):
    """기록(케어 메모와 후 사진 photos 장)을 남기고 완료한 방문. (방문 ID, 사진 ID 목록)을 준다."""
    visit_id = await _started_visit(wired, shop_id, headers)
    media = [await ready_photo(wired, shop_id, headers) for _ in range(photos)]
    written = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
        json={"care_note": "눈물 자국을 닦았어요",
              "media": [{"media_id": m, "phase": "after", "sort_order": i} for i, m in enumerate(media)]})
    assert written.status_code == 200, written.text
    await _complete(wired, shop_id, headers, visit_id)
    return visit_id, media


async def _staff(wired, shop_id, owner):
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    return bearer(staff["access_token"])


async def test_직원이_알림장을_미리_보고_설정과_링크가_그대로_비친다(wired, media_storage):
    from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
    from core.link_token import read_token

    shop_id, owner, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    visit_id = await _started_visit(wired, shop_id, o)
    photo = await ready_photo(wired, shop_id, o)
    written = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=o,
        json={"weight_kg": 3.4, "care_note": "눈물 자국을 닦았어요", "internal_note": "SECRET-내부메모",
              "media": [{"media_id": photo, "phase": "after", "sort_order": 0}]})
    assert written.status_code == 200, written.text
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/report"

    seen = await wired.api.get(path, headers=bearer(staff["access_token"]))
    assert seen.status_code == 200, seen.text
    [media] = seen.json()["report"].pop("media")
    assert seen.json() == {
        "report": {
            "pet_name": "콩이", "visit_date": YESTERDAY.isoformat(), "care_note": "눈물 자국을 닦았어요",
            "media": [media], "cover": {"url": media["display_url"], "width": 3000, "height": 2000},
            "menus": [], "total_amount": None, "weight_kg": None,
            "shop": {"name": "Hiss Haus", "phone": None, "address": None},
            "review_url": None, "review_text": None,
        },
        "link": NO_LINK,
        "settings": {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": False,
                     "show_amount": False, "review_url": None, "review_text": None, "review_text_default": "미용이 마음에 드셨다면 후기를 남겨 주세요"},
    }
    assert (media["media_id"], media["hidden"], media["kind"], media["phase"]) == (photo, False, "photo", "after")
    assert "response-content-disposition" in media["download_url"]
    assert "response-content-disposition" not in media["display_url"]
    # 서명 주소의 질의 문자열(16진 서명)은 떼고 본다 — 숫자 조각이 서명과 우연히 겹친다.
    shown = re.sub(r'\?[^"]*', "", seen.text)
    assert "SECRET" not in shown and "김민지" not in shown and "1234" not in shown

    changed = await wired.api.put(
        f"/v1/shops/{shop_id}/report-settings", headers=o,
        json={"link_days": 7, "show_menus": False, "show_shop_info": False, "show_weight": True,
              "show_amount": False})
    assert changed.status_code == 200, changed.text
    await _complete(wired, shop_id, o, visit_id)
    sent = await wired.api.put(path, headers=o, json={"hidden_media_ids": [photo]})
    assert sent.status_code == 200, sent.text

    body = (await wired.api.get(path, headers=o)).json()
    assert body == sent.json()
    assert (body["report"]["menus"], body["report"]["shop"], body["report"]["weight_kg"]) == (None, None, 3.4)
    assert ([m["hidden"] for m in body["report"]["media"]], body["report"]["cover"]) == ([True], None)
    assert body["settings"]["show_weight"] is True
    assert body["link"]["status"] == "live"
    token = re.fullmatch(re.escape(REPORT_WEB_BASE_URL) + r"/r/([A-Za-z0-9_-]{43})", body["link"]["url"]).group(1)
    assert len(read_token(token, REPORT_LINK_KEY)) == 16
    assert body["link"]["expires_at"].endswith("+09:00") and body["link"]["created_at"].endswith("+09:00")
    sent_at, expires_at = (datetime.fromisoformat(body["link"][k]) for k in ("created_at", "expires_at"))
    assert expires_at - sent_at == timedelta(days=7)


async def test_다른_매장의_방문은_미리_볼_수_없고_기록이_없으면_409_다(wired):
    """R2"""
    operator = await make_operator(wired)
    a_shop, _, a = await _shop(wired, operator, "A 매장", "A사장")
    b_shop, _, b = await _shop(wired, operator, "B 매장", "B사장")
    b_visit = await _started_visit(wired, b_shop, b)
    assert (await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/record", headers=b,
                                json={"care_note": "B 매장의 메모"})).status_code == 200
    a_visit = await _started_visit(wired, a_shop, a)

    assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/visits/{b_visit}/report", headers=a)) == (
        404, "VISIT_NOT_FOUND")
    assert error_of(await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=a)) == (
        403, "NOT_A_MEMBER")
    assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/visits/{a_visit}/report", headers=a)) == (
        409, "VISIT_NO_RECORD_YET")
    assert (await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=b)).status_code == 200


async def test_사장과_직원이_보내면_같은_링크이고_끊은_뒤_다시_보내면_새_링크다(wired):
    """R4 — 끊은 링크는 새 링크를 만들어도 되살아나지 않는다(줄이 다르다)."""
    shop_id, owner, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    staff = await _staff(wired, shop_id, owner)
    visit_id, _ = await _completed_visit(wired, shop_id, o)
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/report"

    first = await wired.api.put(path, headers=o, json={"hidden_media_ids": []})
    assert (first.status_code, first.json()["link"]["status"]) == (200, "live")
    again = await wired.api.put(path, headers=staff, json={"hidden_media_ids": []})
    assert (again.status_code, again.json()["link"]) == (200, first.json()["link"])

    assert (await wired.api.delete(path, headers=staff)).status_code == 204
    assert (await wired.api.get(path, headers=o)).json()["link"] == NO_LINK
    assert error_of(await wired.api.delete(path, headers=o)) == (404, "REPORT_NOT_FOUND")

    second = await wired.api.put(path, headers=staff, json={"hidden_media_ids": []})
    assert (second.status_code, second.json()["link"]["status"]) == (200, "live")
    assert second.json()["link"]["url"] != first.json()["link"]["url"]
    async with wired.engine.connect() as conn:
        rows = (await conn.execute(text(
            "SELECT revoked_at IS NULL, created_by_member_id FROM visit_reports ORDER BY id"))).all()
    assert [live for live, _ in rows] == [False, True]
    assert rows[0][1] != rows[1][1]   # 사장이 만든 줄, 직원이 만든 줄


async def test_완료_전이거나_보낼_것이_없으면_거절하고_링크를_만들지_않는다(wired):
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id = await _started_visit(wired, shop_id, o)
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
    assert (await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=o,
                                json={"weight_kg": 3.4})).status_code == 200   # 메모도 사진도 없는 기록

    assert error_of(await wired.api.put(path, headers=o, json={"hidden_media_ids": []})) == (
        409, "VISIT_NOT_COMPLETED")
    await _complete(wired, shop_id, o, visit_id)
    assert error_of(await wired.api.put(path, headers=o, json={"hidden_media_ids": []})) == (422, "REPORT_EMPTY")
    assert error_of(await wired.api.put(path, headers=o, json={"hidden_media_ids": [999]})) == (
        422, "VALIDATION_ERROR")
    async with wired.engine.connect() as conn:
        assert (await conn.execute(text("SELECT count(*) FROM visit_reports"))).scalar_one() == 0


async def test_다른_매장의_방문에는_보내지도_끊지도_못한다(wired):
    """R2"""
    operator = await make_operator(wired)
    a_shop, _, a = await _shop(wired, operator, "A 매장", "A사장")
    b_shop, _, b = await _shop(wired, operator, "B 매장", "B사장")
    b_visit, _ = await _completed_visit(wired, b_shop, b)
    sent = await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=b,
                               json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text

    through_mine = f"/v1/shops/{a_shop}/visits/{b_visit}/report"
    assert error_of(await wired.api.put(through_mine, headers=a, json={"hidden_media_ids": []})) == (
        404, "VISIT_NOT_FOUND")
    assert error_of(await wired.api.delete(through_mine, headers=a)) == (404, "VISIT_NOT_FOUND")
    theirs = f"/v1/shops/{b_shop}/visits/{b_visit}/report"
    assert error_of(await wired.api.put(theirs, headers=a, json={"hidden_media_ids": []})) == (403, "NOT_A_MEMBER")
    assert error_of(await wired.api.delete(theirs, headers=a)) == (403, "NOT_A_MEMBER")

    assert (await wired.api.get(theirs, headers=b)).json()["link"] == sent.json()["link"]   # 그대로 살아 있다


async def test_알림장에서_뺀_사진은_기록을_고치고_사진을_덧붙여도_빠져_있다(wired, media_storage):
    """R5"""
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id, [first, removed, last] = await _completed_visit(wired, shop_id, o, photos=3)
    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
    sent = await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": [removed]})
    assert sent.status_code == 200, sent.text

    async def hidden():
        media = (await wired.api.get(f"{visit}/report", headers=o)).json()["report"]["media"]
        return {m["media_id"]: m["hidden"] for m in media}

    assert await hidden() == {first: False, removed: True, last: False}

    rewritten = await wired.api.put(
        f"{visit}/record", headers=o,
        json={"version": 1, "care_note": "메모만 고쳤어요",
              "media": [{"media_id": m, "phase": "after", "sort_order": i}
                        for i, m in enumerate([last, removed, first])]})   # 자리도 바꿨다
    assert rewritten.status_code == 200, rewritten.text
    assert await hidden() == {first: False, removed: True, last: False}

    added = await ready_photo(wired, shop_id, o)
    appended = await wired.api.post(f"{visit}/record/media", headers=o, json={"media_id": added, "phase": "after"})
    assert appended.status_code == 200, appended.text
    assert await hidden() == {first: False, removed: True, last: False, added: False}
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"] == sent.json()["link"]


async def test_보낸_방문은_되돌리지_못하고_끊으면_되돌려진다(wired):
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id, _ = await _completed_visit(wired, shop_id, o)
    report = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
    revert = {"visit_ids": [visit_id], "action": "revert"}
    assert (await wired.api.put(report, headers=o, json={"hidden_media_ids": []})).status_code == 200

    assert error_of(await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o, json=revert)) == (
        409, "VISIT_REPORT_SENT")
    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=o)).json()
    assert (detail["visit"]["status"], detail["report"]["status"]) == ("completed", "live")

    assert (await wired.api.delete(report, headers=o)).status_code == 204
    reverted = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o, json=revert)
    assert (reverted.status_code, reverted.json()["visits"][0]["status"]) == (200, "reserved")


async def test_보낸_방문의_기록은_지우지_못하고_끊으면_지워진다(wired, media_storage):
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id, [photo] = await _completed_visit(wired, shop_id, o, photos=1)
    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
    assert (await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})).status_code == 200

    assert error_of(await wired.api.delete(f"{visit}/record", headers=o)) == (409, "VISIT_REPORT_SENT")
    kept = (await wired.api.get(visit, headers=o)).json()["record"]
    assert [m["media_id"] for m in kept["media"]] == [photo]

    assert (await wired.api.delete(f"{visit}/report", headers=o)).status_code == 204
    assert (await wired.api.delete(f"{visit}/record", headers=o)).status_code == 204
    assert (await wired.api.get(visit, headers=o)).json()["record"] is None


async def test_고객을_삭제하면_그_고객의_알림장_링크가_끊긴다(wired):
    """R19"""
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id, _ = await _completed_visit(wired, shop_id, o)
    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
    assert (await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})).status_code == 200
    customer_id = (await wired.api.get(visit, headers=o)).json()["visit"]["customer"]["customer_id"]

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204

    assert (await wired.api.get(visit, headers=o)).json()["report"] == NO_LINK
    async with wired.engine.connect() as conn:
        rows = (await conn.execute(text("SELECT revoked_at IS NOT NULL FROM visit_reports"))).all()
    assert rows == [(True,)]


async def test_익명화한_고객의_방문에는_다시_보내지_못한다(wired):
    """가족 잠금이 익명화한 고객을 거절한다 — 오류 코드는 VISIT_… 가 아니라 CUSTOMER_NOT_FOUND 다."""
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id, _ = await _completed_visit(wired, shop_id, o)
    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
    assert (await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})).status_code == 200
    customer_id = (await wired.api.get(visit, headers=o)).json()["visit"]["customer"]["customer_id"]
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204

    seen = [
        error_of(await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})),
        error_of(await wired.api.delete(f"{visit}/report", headers=o)),
        error_of(await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o,
                                      json={"visit_ids": [visit_id], "action": "revert"})),
        error_of(await wired.api.delete(f"{visit}/record", headers=o)),
    ]

    assert seen == [(404, "CUSTOMER_NOT_FOUND")] * 4
    async with wired.engine.connect() as conn:
        live = (await conn.execute(text(
            "SELECT count(*) FROM visit_reports WHERE visit_id = :id AND revoked_at IS NULL"), {"id": visit_id}))
        assert live.scalar_one() == 0
    detail = (await wired.api.get(visit, headers=o)).json()
    assert (detail["visit"]["status"], detail["record"] is None, detail["report"]) == ("completed", False, NO_LINK)


async def test_보낸_방문은_상세와_하루_목록과_피드에_보냄으로_나온다(wired):
    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    visit_id, _ = await _completed_visit(wired, shop_id, o)
    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"

    async def seen():
        detail = (await wired.api.get(visit, headers=o)).json()
        day = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={YESTERDAY.isoformat()}", headers=o)).json()
        feed = (await wired.api.get(f"/v1/shops/{shop_id}/visits/feed", headers=o)).json()
        return detail["report"], [i["report_sent"] for i in day["items"]], [i["report_sent"] for i in feed["items"]]

    assert await seen() == (NO_LINK, [False], [False])
    sent = await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    assert await seen() == (sent.json()["link"], [True], [True])
    assert (await wired.api.delete(f"{visit}/report", headers=o)).status_code == 204
    assert await seen() == (NO_LINK, [False], [False])
