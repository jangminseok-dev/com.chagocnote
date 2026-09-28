"""알림장을 실제 배선(프로바이더·허브 포트 조립·설정 상수·DB·MinIO)으로 확인한다."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

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
NO_LINK = {"status": "none", "url": None, "expires_at": None, "first_viewed_at": None, "created_at": None}
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


async def test_직원이_알림장을_미리_보고_설정과_링크가_그대로_비친다(wired, media_storage):
    from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
    from visit.domain.services.report_token import read_token

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
        },
        "link": NO_LINK,
        "settings": {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": False,
                     "show_amount": False},
    }
    assert (media["media_id"], media["hidden"], media["kind"], media["phase"]) == (photo, False, "photo", "after")
    assert "response-content-disposition" in media["download_url"]
    assert "response-content-disposition" not in media["display_url"]
    assert "SECRET" not in seen.text and "김민지" not in seen.text and "1234" not in seen.text

    changed = await wired.api.put(
        f"/v1/shops/{shop_id}/report-settings", headers=o,
        json={"link_days": 7, "show_menus": False, "show_shop_info": False, "show_weight": True,
              "show_amount": False})
    assert changed.status_code == 200, changed.text
    await wired.execute(
        "UPDATE visit_record_media SET hidden_from_report = true WHERE media_id = :id", id=photo)
    await wired.execute(
        "INSERT INTO visit_reports (visit_id, public_id, expires_at, created_by_member_id, created_at)"
        " VALUES (:visit_id, :public_id, now() + interval '7 days', 1, now())",
        visit_id=visit_id, public_id=bytes(range(16)))

    body = (await wired.api.get(path, headers=o)).json()
    assert (body["report"]["menus"], body["report"]["shop"], body["report"]["weight_kg"]) == (None, None, 3.4)
    assert ([m["hidden"] for m in body["report"]["media"]], body["report"]["cover"]) == ([True], None)
    assert body["settings"]["show_weight"] is True
    assert body["link"]["status"] == "live"
    token = re.fullmatch(re.escape(REPORT_WEB_BASE_URL) + r"/r/([A-Za-z0-9_-]{43})", body["link"]["url"]).group(1)
    assert read_token(token, REPORT_LINK_KEY) == bytes(range(16))
    assert body["link"]["expires_at"].endswith("+09:00") and body["link"]["created_at"].endswith("+09:00")


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
