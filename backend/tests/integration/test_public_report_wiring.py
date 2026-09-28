"""로그인 없이 열리는 공개 알림장을 실제 배선(프로바이더·허브 포트 조립·DB·Redis·MinIO)으로 확인한다.

검토 기준은 하나다 — 공개하기로 한 것 말고는 아무것도 나가지 않는다.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import bearer, error_of, make_operator, ready_photo, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
YESTERDAY = datetime.now(SEOUL).date() - timedelta(days=1)
# 어디에도 나가면 안 되는 칸에는 표식(SECRET)을 넣는다. 결제 수단은 고를 수 있는 값이 정해져 있어 그 값을 찾는다.
CUSTOMER = {"name": "SECRET보호자", "phone": "010-9876-5432", "marketing_consent": True, "memo": "SECRET-고객메모"}
PET = {"name": "콩이", "species": "dog", "breed": "SECRET품종", "sex": "female", "neutered": True,
       "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True, "memo": "SECRET-아이메모"}
LEAKS = ("SECRET", "9876", "5432", "transfer", "payment", "internal", "memo", "hidden",
         "media_id", "visit_id", "customer_id", "pet_id", "shop_id", "member")
ALL_ON = {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": True, "show_amount": True}
PUBLIC = "/v1/public/report"
VIEWED = "/v1/public/report/viewed"


def _token(link: dict) -> str:
    return link["url"].rsplit("/r/", 1)[1]


def _with(token: str) -> dict:
    return {"X-Report-Token": token}


async def _shop(wired, name="Hiss Haus", owner_name="사장님"):
    shop_id, owner = await shop_with_owner(wired, await make_operator(wired, f"{name} 운영자"), name, owner_name)
    return shop_id, bearer(owner["access_token"])


async def _completed_visit(wired, shop_id, headers, photos=0, phone=CUSTOMER["phone"]):
    """모든 칸을 채운 기록(후 사진 photos 장)을 남기고 완료한 콩이의 어제 방문. (방문 주소, 사진 ID 목록, 메뉴 이름)."""
    family = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                  json={"customer": {**CUSTOMER, "phone": phone}, "pet": PET})
    assert family.status_code == 201, family.text
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": family.json()["customer"]["customer_id"],
              "pet_ids": [family.json()["pets"][0]["pet_id"]], "memo": "SECRET-예약메모",
              "starts_at": datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 11, tzinfo=SEOUL).isoformat()})
    assert booked.status_code == 201, booked.text
    visit = f"/v1/shops/{shop_id}/visits/{booked.json()['visits'][0]['visit_id']}"
    media = [await ready_photo(wired, shop_id, headers) for _ in range(photos)]
    bath = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"][0]
    for action, body in (
        ("start", None),
        ("record", {"weight_kg": 3.4, "care_note": "눈물 자국을 닦았어요", "internal_note": "SECRET-내부메모",
                    "payment_method": "transfer", "total_amount": 25000,
                    "items": [{"menu_id": bath["menu_id"], "amount": 28000}],
                    "media": [{"media_id": m, "phase": "after", "sort_order": i} for i, m in enumerate(media)]}),
        ("complete", None),
    ):
        if body is None:
            done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                        json={"visit_ids": [booked.json()["visits"][0]["visit_id"]], "action": action})
        else:
            done = await wired.api.put(f"{visit}/record", headers=headers, json=body)
        assert done.status_code == 200, done.text
    return visit, media, bath["name"]


async def _settings(wired, shop_id, headers, **changes) -> None:
    changed = await wired.api.put(f"/v1/shops/{shop_id}/report-settings", headers=headers,
                                  json={**ALL_ON, **changes})
    assert changed.status_code == 200, changed.text


async def _send(wired, visit, headers, hidden=()) -> str:
    sent = await wired.api.put(f"{visit}/report", headers=headers, json={"hidden_media_ids": list(hidden)})
    assert sent.status_code == 200, sent.text
    return _token(sent.json()["link"])


async def test_모든_항목을_켜도_공개하기로_한_것만_나간다(wired, media_storage):
    """R6"""
    shop_id, o = await _shop(wired)
    assert (await wired.api.put(f"/v1/shops/{shop_id}/settings", headers=o,
                                json={"name": "Hiss Haus", "phone": "02-123-4567", "address": "서울 어딘가"})
            ).status_code == 200
    visit, [shown, removed], bath = await _completed_visit(wired, shop_id, o, photos=2)
    await _settings(wired, shop_id, o)
    token = await _send(wired, visit, o, hidden=[removed])
    preview = (await wired.api.get(f"{visit}/report", headers=o)).json()
    by_id = {m["media_id"]: m for m in preview["report"]["media"]}

    response = await wired.api.get(PUBLIC, headers=_with(token))

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    body = response.json()
    [media] = body.pop("media")
    assert body == {
        "pet_name": "콩이", "visit_date": YESTERDAY.isoformat(), "care_note": "눈물 자국을 닦았어요",
        "cover": {"url": media["display_url"], "width": 3000, "height": 2000},
        "menus": [{"name": bath, "amount": 28000}], "total_amount": 25000, "weight_kg": 3.4,
        "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": "서울 어딘가"},
        "expires_at": preview["link"]["expires_at"],
    }
    assert body["expires_at"].endswith("+09:00")
    assert media == {k: v for k, v in by_id[shown].items() if k not in ("media_id", "hidden")}
    assert set(media) == {"kind", "phase", "width", "height", "duration_seconds", "display_url", "thumb_url",
                          "download_url"}
    # 본문 글 전체에 — 칸 이름으로도 값으로도 — 없어야 한다.
    assert [word for word in LEAKS if word in response.text] == []
    assert token not in response.text
    # 뺀 사진은 어느 주소로도 나가지 않는다.
    for url in (by_id[removed][k] for k in ("display_url", "thumb_url", "download_url")):
        assert url.split("?")[0] not in response.text


@pytest.mark.parametrize(("off", "missing"), [
    ({"show_menus": False}, {"menus"}),
    ({"show_amount": False}, {"total_amount"}),
    ({"show_weight": False}, {"weight_kg"}),
    ({"show_shop_info": False}, {"shop"}),
], ids=["메뉴", "금액", "몸무게", "매장 정보"])
async def test_설정에서_끈_항목은_응답에_칸이_없다(wired, off, missing):
    """R7 — 이미 보낸 알림장에도 바로 적용된다."""
    shop_id, o = await _shop(wired)
    visit, _, bath = await _completed_visit(wired, shop_id, o)
    await _settings(wired, shop_id, o)
    token = await _send(wired, visit, o)
    full = (await wired.api.get(PUBLIC, headers=_with(token))).json()

    await _settings(wired, shop_id, o, **off)
    body = (await wired.api.get(PUBLIC, headers=_with(token))).json()

    assert set(full) - set(body) == missing
    if off == {"show_amount": False}:
        assert body["menus"] == [{"name": bath}]
        assert "28000" not in str(body) and "25000" not in str(body)


async def test_보내고_열고_끊고_다시_보낸다(wired):
    """R3·R4·R11"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    first = await _send(wired, visit, o)

    assert (await wired.api.get(PUBLIC, headers=_with(first))).status_code == 200
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None
    viewed = await wired.api.post(VIEWED, headers=_with(first))
    assert (viewed.status_code, viewed.content) == (204, b"")
    seen_at = (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"]
    assert seen_at is not None and seen_at.endswith("+09:00")
    assert (await wired.api.post(VIEWED, headers=_with(first))).status_code == 204
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] == seen_at

    assert (await wired.api.delete(f"{visit}/report", headers=o)).status_code == 204
    for closed in (await wired.api.get(PUBLIC, headers=_with(first)),
                   await wired.api.post(VIEWED, headers=_with(first))):
        assert error_of(closed) == (410, "REPORT_CLOSED")
        assert set(closed.json()) == {"code", "message"}
        assert [word for word in ("콩이", "Hiss", *LEAKS) if word in closed.text] == []

    second = await _send(wired, visit, o)
    assert second != first
    assert error_of(await wired.api.get(PUBLIC, headers=_with(first))) == (410, "REPORT_CLOSED")
    assert (await wired.api.get(PUBLIC, headers=_with(second))).status_code == 200
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None


async def test_기간이_지난_링크는_410_이고_열람을_남기지_않는다(wired):
    """R3·R11"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)
    await wired.execute("UPDATE visit_reports SET created_at = now() - interval '2 days', "
                        "expires_at = now() - interval '1 second'")

    assert error_of(await wired.api.get(PUBLIC, headers=_with(token))) == (410, "REPORT_CLOSED")
    assert error_of(await wired.api.post(VIEWED, headers=_with(token))) == (410, "REPORT_CLOSED")
    async with wired.engine.connect() as conn:
        assert (await conn.execute(text("SELECT first_viewed_at FROM visit_reports"))).all() == [(None,)]


@pytest.mark.parametrize("column", ["suspended_at", "closed_at"])
async def test_정지하거나_폐업한_매장의_알림장은_410_이고_풀리면_다시_열린다(wired, column):
    """R21"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    await wired.execute(f"UPDATE shops SET {column} = now() WHERE id = :id", id=shop_id)
    closed = await wired.api.get(PUBLIC, headers=_with(token))
    assert error_of(closed) == (410, "REPORT_CLOSED")
    assert "Hiss" not in closed.text
    assert error_of(await wired.api.post(VIEWED, headers=_with(token))) == (410, "REPORT_CLOSED")

    await wired.execute(f"UPDATE shops SET {column} = NULL WHERE id = :id", id=shop_id)
    assert (await wired.api.get(PUBLIC, headers=_with(token))).status_code == 200
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None


async def test_고객을_삭제하면_그_고객의_알림장은_410_이다(wired):
    """R19"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)
    customer_id = (await wired.api.get(visit, headers=o)).json()["visit"]["customer"]["customer_id"]
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204

    assert error_of(await wired.api.get(PUBLIC, headers=_with(token))) == (410, "REPORT_CLOSED")
    assert error_of(await wired.api.post(VIEWED, headers=_with(token))) == (410, "REPORT_CLOSED")


async def test_다른_매장의_알림장과_섞이지_않는다(wired):
    a_shop, a = await _shop(wired, "A 매장", "A사장")
    b_shop, b = await _shop(wired, "B 매장", "B사장")
    a_visit, _, _ = await _completed_visit(wired, a_shop, a)
    b_visit, _, _ = await _completed_visit(wired, b_shop, b)
    assert (await wired.api.put(f"{b_visit}/record", headers=b,
                                json={"version": 1, "care_note": "B 매장의 메모"})).status_code == 200
    a_token, b_token = await _send(wired, a_visit, a), await _send(wired, b_visit, b)

    seen = [(await wired.api.get(PUBLIC, headers=_with(t))).json() for t in (a_token, b_token)]
    assert [(s["shop"]["name"], s["care_note"]) for s in seen] == [
        ("A 매장", "눈물 자국을 닦았어요"), ("B 매장", "B 매장의 메모")]


@pytest.mark.parametrize("headers", [
    {}, {"X-Report-Token": ""}, {"X-Report-Token": "a" * 42}, {"X-Report-Token": "a" * 44},
    {"X-Report-Token": "a" * 5000}, {"X-Report-Token": "알림장".encode()}, {"X-Report-Token": " "},
    {"X-Report-Token": "a" * 43},
], ids=["헤더 없음", "빈 값", "42글자", "44글자", "5000글자", "한글", "공백", "서명 없는 43글자"])
async def test_이상한_토큰은_404_다(wired, headers):
    """R13"""
    for response in (await wired.api.get(PUBLIC, headers=headers), await wired.api.post(VIEWED, headers=headers)):
        assert error_of(response) == (404, "REPORT_NOT_FOUND")
        assert set(response.json()) == {"code", "message"}


async def test_패딩을_붙이거나_다른_키로_서명한_토큰은_404_다(wired):
    """R13"""
    from core.config import REPORT_LINK_KEY
    from visit.domain.services.report_token import make_token, read_token

    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)
    forged = make_token(read_token(token, REPORT_LINK_KEY), bytes(32))

    for wrong in (token + "=", forged, token[:-1], token.swapcase()):
        assert error_of(await wired.api.get(PUBLIC, headers=_with(wrong))) == (404, "REPORT_NOT_FOUND")
    assert (await wired.api.get(PUBLIC, headers=_with(token))).status_code == 200


async def test_로그인_토큰은_공개_조회에_아무_뜻이_없다(wired):
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    assert error_of(await wired.api.get(PUBLIC, headers=o)) == (404, "REPORT_NOT_FOUND")
    broken = {"Authorization": "Bearer 깨진토큰".encode(), "X-Report-Token": token}
    assert (await wired.api.get(PUBLIC, headers=broken)).status_code == 200


async def test_1분에_61번째_요청부터_429_다(wired):
    """R1"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    codes = [(await wired.api.get(PUBLIC, headers=_with(token))).status_code for _ in range(61)]
    assert codes == [200] * 60 + [429]
    blocked = await wired.api.post(VIEWED, headers=_with(token))
    assert error_of(blocked) == (429, "TOO_MANY_ATTEMPTS")
    assert set(blocked.json()) == {"code", "message"}
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None


async def test_실패가_20번이어도_맞는_토큰은_열리고_틀린_토큰은_접속_주소_헤더를_바꿔도_429_다(wired, monkeypatch):
    """R1·R17 — 검토 지적: 실패 수 차단은 서명이 틀린 요청에만 건다. 맞는 토큰은 남의 실패로 막히지 않는다.
    비밀값 없이 보낸 X-Report-Client-IP 는 믿지 않는다. 틀린 토큰은 모두 연결된 주소 하나로 센다."""
    from visit.dependencies import public_client

    monkeypatch.setattr(public_client, "REPORT_WEB_SECRET", "web-secret-for-test")
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    async def guess(n, secret):
        return (await wired.api.get(PUBLIC, headers={
            "X-Report-Token": "a" * 43, "X-Report-Client-IP": f"203.0.113.{n}", "X-Report-Web-Secret": secret,
        })).status_code

    # 틀린 토큰(서명 불일치)으로 20번 실패 — 비밀값이 틀려 모두 같은 연결된 주소로 센다.
    assert [await guess(n, "틀린-비밀값".encode()) for n in range(20)] == [404] * 20
    # 실패가 찼어도 맞는 토큰은 그대로 열린다 — 남의 실패로 막히지 않는다.
    assert (await wired.api.get(PUBLIC, headers=_with(token))).status_code == 200
    # 열람 신호도 같은 관문이다 — 실패가 찬 뒤에도 맞는 토큰의 열람은 204.
    assert (await wired.api.post(VIEWED, headers=_with(token))).status_code == 204
    # 틀린 토큰은 21번째부터 429다 — 접속 주소 헤더를 바꿔도(비밀값이 틀려) 피하지 못한다.
    assert error_of(await wired.api.get(PUBLIC, headers={
        "X-Report-Token": "a" * 43, "X-Report-Client-IP": "203.0.113.99", "X-Report-Web-Secret": "또다른-비밀값".encode(),
    })) == (429, "TOO_MANY_ATTEMPTS")
    # 비밀값이 맞으면 웹 서버가 알려 준 주소로 센다 — 새 주소는 아직 막히지 않았다.
    assert (await wired.api.get(PUBLIC, headers={
        **_with(token), "X-Report-Client-IP": "198.51.100.9", "X-Report-Web-Secret": "web-secret-for-test",
    })).status_code == 200
    # 비밀값이 맞아 각각 다른 주소로 세어지면 한 번씩의 실패는 막히지 않는다.
    assert [await guess(n, "web-secret-for-test") for n in range(21)] == [404] * 21


async def test_공개_조회는_토큰을_로그에_남기지_않는다(wired, caplog):
    """R18 — 성공·404·410·429 를 모두 지난 뒤 잡힌 로그 전체를 본다."""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    live = await _send(wired, visit, o)
    closed_visit, _, _ = await _completed_visit(wired, shop_id, o, phone="010-2222-3333")
    closed = await _send(wired, closed_visit, o)
    assert (await wired.api.delete(f"{closed_visit}/report", headers=o)).status_code == 204
    wrong = live.swapcase()

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        seen = [(await wired.api.get(PUBLIC, headers=_with(t))).status_code for t in (live, wrong, closed)]
        seen += [(await wired.api.post(VIEWED, headers=_with(t))).status_code for t in (live, wrong, closed)]
        for _ in range(60):
            last = await wired.api.get(PUBLIC, headers=_with(live))
        logging.getLogger("tests.public_report").debug("로그가 잡히는지 확인하는 줄")

    assert (seen, last.status_code) == ([200, 404, 410, 204, 404, 410], 429)
    assert "로그가 잡히는지 확인하는 줄" in caplog.text
    logged = caplog.text + "".join(repr(r.args) for r in caplog.records)
    assert [t for t in (live, wrong, closed) if t in logged] == []
