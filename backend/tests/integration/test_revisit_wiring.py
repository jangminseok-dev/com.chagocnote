"""⑬ 미용 주기 · 다시 올 때가 된 아이 · 결제 완료와 남은 일 · 하루 마무리 — 조립된 앱과 실제 DB."""
import pytest

from tests.integration.support import error_of
from tests.integration.test_sales_wiring import _shop, _staff

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
