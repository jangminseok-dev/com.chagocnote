"""문진표의 설정과 매장이 더한 질문을 실제 배선으로 확인한다(⑪-C)."""
import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import count
from tests.integration.test_form_settings_wiring import put, read
from tests.integration.test_visit_checks_wiring import _shop, _staff

pytestmark = pytest.mark.integration


async def questions(wired, shop_id, headers):
    return await wired.api.get(f"/v1/shops/{shop_id}/intake-questions", headers=headers)


async def save(wired, shop_id, headers, *items):
    return await wired.api.put(f"/v1/shops/{shop_id}/intake-questions", headers=headers, json={"items": list(items)})


def q(label, required=False, question_id=None):
    return {"question_id": question_id, "label": label, "required": required}


async def test_문진표의_설정은_기본값이_있고_바꾸면_그대로_읽힌다(wired):
    shop_id, headers, _ = await _shop(wired)

    got = (await read(wired, shop_id, headers)).json()
    assert (got["intake_keep_days"], got["intake_hidden"]) == (30, [])
    assert (got["defaults"]["intake_keep_days"], got["defaults"]["intake_hidden"]) == (30, [])

    changed = await put(wired, shop_id, headers, intake_keep_days=14, intake_hidden=["weight", "style"])
    assert changed.status_code == 200, changed.text
    assert ((await read(wired, shop_id, headers)).json()["intake_keep_days"], changed.json()["intake_hidden"]) == (
        14, ["weight", "style"])
    assert error_of(await put(wired, shop_id, headers, intake_keep_days=91)) == (422, "VALIDATION_ERROR")
    assert error_of(await put(wired, shop_id, headers, intake_hidden=["pet_name"])) == (422, "VALIDATION_ERROR")


async def test_예전_앱이_다섯_칸만_보내도_문진표의_설정은_그대로다(wired):
    shop_id, headers, _ = await _shop(wired)
    await put(wired, shop_id, headers, intake_keep_days=14, intake_hidden=["weight"])

    old_app = await put(wired, shop_id, headers, link_days=7)        # 도우미는 다섯 칸만 보낸다

    assert old_app.status_code == 200, old_app.text
    got = old_app.json()
    assert (got["link_days"], got["intake_keep_days"], got["intake_hidden"]) == (7, 14, ["weight"])


async def test_질문을_더하고_고치고_지우면_순서대로_보이고_지운_질문의_행은_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    assert (await questions(wired, shop_id, headers)).json() == {"items": []}

    saved = await save(wired, shop_id, headers, q("산책은 얼마나 하나요?"), q("간식 알레르기가 있나요?", required=True))
    assert saved.status_code == 200, saved.text
    first, second = saved.json()["items"]
    assert set(first) == {"question_id", "label", "required"}
    assert [(i["label"], i["required"]) for i in saved.json()["items"]] == [
        ("산책은 얼마나 하나요?", False), ("간식 알레르기가 있나요?", True)]

    # 둘째를 앞으로 옮기고 글을 고치고, 첫째를 지우고, 하나를 더한다.
    again = await save(wired, shop_id, headers,
                       q("간식 알레르기", required=False, question_id=second["question_id"]), q("다른 병원에 다니나요?"))
    assert [(i["question_id"] == second["question_id"], i["label"]) for i in again.json()["items"]] == [
        (True, "간식 알레르기"), (False, "다른 병원에 다니나요?")]
    assert (await questions(wired, shop_id, headers)).json() == again.json()
    assert await count(wired, "shop_intake_questions") == 3
    assert await count(wired, "shop_intake_questions", "removed_at IS NOT NULL") == 1
    assert first["question_id"] not in [i["question_id"] for i in again.json()["items"]]


async def test_질문은_다섯_개까지이고_빈_글과_긴_글은_받지_않는다(wired):
    shop_id, owner, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)
    other_shop, other, _ = await _shop(wired, "다른 매장", "다른 사장", operator)
    mine = (await save(wired, shop_id, owner, q("질문 하나"))).json()["items"][0]["question_id"]

    assert (await save(wired, shop_id, owner, *[q(f"질문 {n}") for n in range(6)])).status_code == 422
    assert error_of(await save(wired, shop_id, owner, q("  "))) == (422, "VALIDATION_ERROR")
    assert (await save(wired, shop_id, owner, q("가" * 101))).status_code == 422
    assert (await save(wired, shop_id, staff, q("직원의 질문"))).status_code == 403
    assert (await questions(wired, shop_id, staff)).status_code == 200
    # 남의 매장의 질문 번호로는 고칠 수 없다 — 없는 번호다.
    assert error_of(await save(wired, other_shop, other, q("남의 것", question_id=mine))) == (422, "VALIDATION_ERROR")
    assert (await questions(wired, other_shop, other)).json() == {"items": []}
    assert [i["label"] for i in (await questions(wired, shop_id, owner)).json()["items"]] == ["질문 하나"]


async def test_문진표에서_모든_아이에게_동의서_받기는_기본_꺼짐이고_바꾸면_남고_빠지면_둔다(wired):
    shop_id, headers, _ = await _shop(wired)

    got = (await read(wired, shop_id, headers)).json()
    assert (got["intake_consent_all"], got["defaults"]["intake_consent_all"]) == (False, False)

    changed = await put(wired, shop_id, headers, intake_consent_all=True)
    assert changed.status_code == 200 and changed.json()["intake_consent_all"] is True

    await put(wired, shop_id, headers, link_days=7)                    # 이 칸을 모르는 예전 앱
    assert (await read(wired, shop_id, headers)).json()["intake_consent_all"] is True

