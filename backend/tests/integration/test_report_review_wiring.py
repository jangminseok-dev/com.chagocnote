"""알림장 끝의 리뷰 주소(⑫ 설계 3.6) — 설정, 공개 한 장·보호자 한 장, 알림장마다 빼기, 미리보기."""
import pytest

from tests.integration.support import error_of
from tests.integration.test_guardian_wiring import claim, web_login
from tests.integration.test_public_report_wiring import ALL_ON, PUBLIC, _completed_visit, _shop, _token, _with

pytestmark = pytest.mark.integration

URL = "https://m.place.naver.com/place/123/review"
DEFAULT_TEXT = "미용이 마음에 드셨다면 후기를 남겨 주세요"


async def put_settings(wired, shop_id, headers, **changes):
    return await wired.api.put(f"/v1/shops/{shop_id}/report-settings", headers=headers, json={**ALL_ON, **changes})


async def send(wired, visit, headers, **body):
    sent = await wired.api.put(f"{visit}/report", headers=headers, json={"hidden_media_ids": [], **body})
    assert sent.status_code == 200, sent.text
    return sent.json()


async def test_리뷰_주소는_기본으로_없고_넣으면_남고_빠진_칸은_지금_값을_둔다(wired):
    shop_id, o = await _shop(wired)

    got = (await wired.api.get(f"/v1/shops/{shop_id}/report-settings", headers=o)).json()
    assert (got["review_url"], got["review_text"], got["review_text_default"]) == (None, None, DEFAULT_TEXT)

    saved = await put_settings(wired, shop_id, o, review_url=URL, review_text="후기 한 줄 부탁드려요")
    assert saved.status_code == 200, saved.text
    assert (saved.json()["review_url"], saved.json()["review_text"]) == (URL, "후기 한 줄 부탁드려요")

    await put_settings(wired, shop_id, o, show_weight=False)                    # 두 칸을 모르는 예전 앱
    kept = (await wired.api.get(f"/v1/shops/{shop_id}/report-settings", headers=o)).json()
    assert (kept["review_url"], kept["review_text"], kept["show_weight"]) == (URL, "후기 한 줄 부탁드려요", False)

    cleared = await put_settings(wired, shop_id, o, review_url=None, review_text=None)
    assert (cleared.json()["review_url"], cleared.json()["review_text"]) == (None, None)


@pytest.mark.parametrize(("url", "text"), [
    ("javascript:alert(1)", None), ("http://naver.me/x", None), ("https://user@naver.me/x", None),
    (URL, "www.evil.example 로 오세요"), (URL, "가" * 61),
])
async def test_틀린_주소나_문구는_422_이고_저장되지_않는다(wired, url, text):
    shop_id, o = await _shop(wired)

    assert error_of(await put_settings(wired, shop_id, o, review_url=url, review_text=text))[0] == 422
    assert (await wired.api.get(f"/v1/shops/{shop_id}/report-settings", headers=o)).json()["review_url"] is None


async def test_주소가_없으면_한_장에_두_칸이_없고_넣으면_기본_문구와_함께_나온다(wired):
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = _token((await send(wired, visit, o))["link"])

    plain = (await wired.api.get(PUBLIC, headers=_with(token))).json()
    assert "review_url" not in plain and "review_text" not in plain

    await put_settings(wired, shop_id, o, review_url=URL)
    shown = (await wired.api.get(PUBLIC, headers=_with(token))).json()
    assert (shown["review_url"], shown["review_text"]) == (URL, DEFAULT_TEXT)


async def test_알림장마다_리뷰_줄을_뺄_수_있고_다시_보내며_켜면_생긴다_보호자_한_장도_같다(wired):
    shop_id, o = await _shop(wired)
    await put_settings(wired, shop_id, o, review_url=URL, review_text="후기 부탁드려요")
    visit, _, _ = await _completed_visit(wired, shop_id, o)

    preview = (await wired.api.get(f"{visit}/report", headers=o)).json()
    assert (preview["report"]["review_url"], preview["report"]["review_text"]) == (URL, "후기 부탁드려요")
    off = await send(wired, visit, o, show_review=False)
    assert off["link"]["show_review"] is False
    assert (off["report"]["review_url"], off["report"]["review_text"]) == (URL, "후기 부탁드려요")   # 미리보기는 주소를 보인다
    token = _token(off["link"])
    guardian = await web_login(wired, "리뷰보호자")
    linked = await claim(wired, guardian, token)
    link_id = linked.json()["link_id"]
    report_id = (await wired.api.get(f"/v1/me/guardian/links/{link_id}/reports", headers=guardian)).json()["items"][0]["report_id"]

    hidden = (await wired.api.get(PUBLIC, headers=_with(token))).json()
    mine = (await wired.api.get(f"/v1/me/guardian/links/{link_id}/reports/{report_id}", headers=guardian)).json()
    assert "review_url" not in hidden and "review_url" not in mine

    on = await send(wired, visit, o, show_review=True)
    assert on["link"]["show_review"] is True and _token(on["link"]) == token        # 같은 링크
    assert (await wired.api.get(PUBLIC, headers=_with(token))).json()["review_text"] == "후기 부탁드려요"


async def test_보낼_때_show_review_를_빼면_켜진_것이다(wired):
    shop_id, o = await _shop(wired)
    await put_settings(wired, shop_id, o, review_url=URL)
    visit, _, _ = await _completed_visit(wired, shop_id, o)

    sent = await send(wired, visit, o)                                  # 이 칸을 모르는 예전 앱

    assert sent["link"]["show_review"] is True
    assert (await wired.api.get(PUBLIC, headers=_with(_token(sent["link"])))).json()["review_url"] == URL
