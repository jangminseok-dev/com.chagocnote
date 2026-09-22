"""고객·반려동물을 실제 배선(프로바이더·DB 커밋·매장 접근 확인)으로 확인한다. 첫 테스트는 테넌트 격리다."""
import pytest

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {
    "name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True,
}


async def _register(wired, shop_id, headers, customer=None, pet=None):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers",
        json={"customer": {**CUSTOMER, **(customer or {})}, "pet": {**PET, **(pet or {})}},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _list(wired, shop_id, headers, query=""):
    response = await wired.api.get(f"/v1/shops/{shop_id}/customers{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_다른_매장의_고객과_반려동물에는_손댈_수_없다(wired):
    """C1 — B매장 경로는 403 NOT_A_MEMBER, 내 매장 경로에 B매장의 ID 를 넣으면 404 다."""
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    b = bearer(b_owner["access_token"])
    b_customer, b_pet = await _register(wired, b_shop, b)
    a = bearer(a_owner["access_token"])
    body = {"customer": CUSTOMER, "pet": PET}
    # B 에 이미 저장된 값과 다르게 해서, 필터가 빠지면 실제로 값이 바뀌는 결함이 드러나게 한다.
    invasive_customer = {**CUSTOMER, "name": "침입자", "phone": "01000000001", "marketing_consent": False}
    invasive_pet = {**PET, "name": "침입", "weight_kg": 9.9}

    their_shop = [
        await wired.api.get(f"/v1/shops/{b_shop}/customers", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/customers/lookup?phone=01012345678", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/customers", json=body, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/customers/{b_customer}", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/customers/{b_customer}", json=CUSTOMER, headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/customers/{b_customer}", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/customers/{b_customer}/pets", json=PET, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/pets/{b_pet}", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/pets/{b_pet}", json=PET, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/pets/{b_pet}/passed-away", headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/pets/{b_pet}/passed-away", headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/pets/{b_pet}", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/pet-condition-types", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/customers/myself", headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * len(their_shop)

    # 경로의 매장은 내 매장이라 소속 확인은 통과한다. 대상은 컨텍스트의 매장 안에서만 찾는다(C9).
    own_shop = [
        (await wired.api.get(f"/v1/shops/{a_shop}/customers/{b_customer}", headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.put(f"/v1/shops/{a_shop}/customers/{b_customer}", json=invasive_customer, headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.delete(f"/v1/shops/{a_shop}/customers/{b_customer}", headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.post(f"/v1/shops/{a_shop}/customers/{b_customer}/pets", json=invasive_pet, headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.get(f"/v1/shops/{a_shop}/pets/{b_pet}", headers=a), "PET_NOT_FOUND"),
        (await wired.api.put(f"/v1/shops/{a_shop}/pets/{b_pet}", json=invasive_pet, headers=a), "PET_NOT_FOUND"),
        (await wired.api.post(f"/v1/shops/{a_shop}/pets/{b_pet}/passed-away", headers=a), "PET_NOT_FOUND"),
    ]
    assert [error_of(r) for r, _ in own_shop] == [(404, code) for _, code in own_shop]

    # 무지개다리 표시 시도가 필터를 빠뜨렸다면 여기서 이미 죽은 것으로 보일 것이다 — 되돌리기 전에 확인한다.
    mid_check = await wired.api.get(f"/v1/shops/{b_shop}/pets/{b_pet}", headers=b)
    assert mid_check.json()["pet"]["passed_away_at"] is None

    rest = [
        (await wired.api.delete(f"/v1/shops/{a_shop}/pets/{b_pet}/passed-away", headers=a), "PET_NOT_FOUND"),
        (await wired.api.delete(f"/v1/shops/{a_shop}/pets/{b_pet}", headers=a), "PET_NOT_FOUND"),
        (await wired.api.get(f"/v1/shops/{a_shop}/customers/lookup?phone=01012345678", headers=a), "CUSTOMER_NOT_FOUND"),
    ]
    assert [error_of(r) for r, _ in rest] == [(404, code) for _, code in rest]
    assert (await _list(wired, a_shop, a))["items"] == []

    # B 매장의 가족은 값까지 그대로다 — 침입 본문이 하나도 먹지 않았는지 확인한다.
    detail = await wired.api.get(f"/v1/shops/{b_shop}/customers/{b_customer}", headers=b)
    customer = detail.json()["customer"]
    assert (customer["name"], customer["phone"], customer["marketing_consent"]) == ("김민지", "01012345678", True)
    pet = detail.json()["pets"][0]
    assert (pet["name"], pet["weight_kg"], pet["passed_away_at"]) == ("콩이", 3.2, None)
    assert [c["customer_id"] for c in (await _list(wired, b_shop, b, "?q=김민지"))["items"]] == [b_customer]
    assert (await _list(wired, b_shop, b, "?q=침입자"))["items"] == []


async def test_등록부터_익명화까지_돈다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])

    customer_id, kong = await _register(wired, shop_id, headers, customer={"phone_alt": "02-123-4567"})
    looked_up = await wired.api.get(f"/v1/shops/{shop_id}/customers/lookup?phone=01012345678", headers=headers)
    assert looked_up.json() == {"customer_id": customer_id, "name": "김민지", "pet_names": ["콩이"]}

    added = await wired.api.post(
        f"/v1/shops/{shop_id}/customers/{customer_id}/pets",
        json={**PET, "name": "두부", "species": "cat", "no_known_conditions": False,
              "conditions": [{"type_code": "patella_luxation", "note": "2기"},
                             {"type_code": "other", "custom_label": "눈물 자국"}]},
        headers=headers,
    )
    assert added.status_code == 201
    dubu = added.json()["pet"]["pet_id"]
    assert [s["name"] for s in added.json()["siblings"]] == ["콩이"]
    assert [(c["label"], c["custom_label"]) for c in added.json()["pet"]["conditions"]] == [
        ("슬개골 탈구", None), ("기타", "눈물 자국"),
    ]

    listed_response = await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=headers)
    assert listed_response.status_code == 200 and "01012345678" not in listed_response.text
    listed = listed_response.json()
    assert listed["pet_count"] == 2
    card = listed["items"][0]
    assert "phone" not in card
    assert (card["name"], card["phone_masked"]) == ("김민지", "010-12··-5678")
    assert [(p["name"], p["has_conditions"]) for p in card["pets"]] == [("콩이", False), ("두부", True)]

    pet_detail = await wired.api.get(f"/v1/shops/{shop_id}/pets/{dubu}", headers=headers)
    assert "01012345678" not in pet_detail.text and pet_detail.json()["owner"]["phone_masked"] == "010-12··-5678"

    detail = await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert (detail.json()["customer"]["phone"], detail.json()["customer"]["phone_alt"]) == ("01012345678", "021234567")

    # 질병을 통째로 바꾸고, 무지개다리를 표시했다가 되돌린다.
    updated = await wired.api.put(
        f"/v1/shops/{shop_id}/pets/{dubu}",
        json={**PET, "name": "두부", "species": "cat", "no_known_conditions": True, "conditions": []},
        headers=headers,
    )
    assert updated.json()["pet"]["has_conditions"] is False
    passed = await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)
    assert passed.json()["pet"]["passed_away_at"] is not None
    assert [p["name"] for p in (await _list(wired, shop_id, headers))["items"][0]["pets"]] == ["두부"]
    everyone = await _list(wired, shop_id, headers, "?include_passed=true")
    assert [(p["name"], p["passed_away"]) for p in everyone["items"][0]["pets"]] == [("콩이", True), ("두부", False)]
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)).status_code == 200

    # 잘못 등록한 아이를 지우고, 마지막 아이는 지울 수 없다.
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{dubu}", headers=headers)).status_code == 204
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/pets/{kong}", headers=headers)) == (409, "LAST_PET")

    # 번호를 바꾸면 검색도 새 번호를 따른다.
    changed = await wired.api.put(
        f"/v1/shops/{shop_id}/customers/{customer_id}",
        json={**CUSTOMER, "phone": "010-9999-0000"}, headers=headers,
    )
    assert changed.json()["customer"]["phone"] == "01099990000"
    assert [c["customer_id"] for c in (await _list(wired, shop_id, headers, "?q=0000"))["items"]] == [customer_id]
    assert (await _list(wired, shop_id, headers, "?q=5678"))["items"] == []

    # 익명화(C6) — 조회·검색·번호 조회에서 사라지고, 같은 번호로 다시 등록하면 새 고객이다(C3).
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204
    gone = [
        await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers),
        await wired.api.get(f"/v1/shops/{shop_id}/customers/lookup?phone=01099990000", headers=headers),
        await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers),
    ]
    assert [error_of(r) for r in gone] == [(404, "CUSTOMER_NOT_FOUND")] * 3
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/pets/{kong}", headers=headers)) == (404, "PET_NOT_FOUND")
    for query in ("", "?include_passed=true", "?q=김민지", "?q=0000", "?q=ㅋㅇ"):
        assert (await _list(wired, shop_id, headers, query))["items"] == [], query
    again, _ = await _register(wired, shop_id, headers, customer={"phone": "01099990000"})
    assert again != customer_id


async def test_직원은_등록하고_고치지만_고객을_삭제하지_못한다(wired):
    """C4 — customer:delete 는 사장만 가진다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    headers = bearer(staff["access_token"])

    customer_id, pet_id = await _register(wired, shop_id, headers)
    assert (await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}", json=CUSTOMER, headers=headers)).status_code == 200
    assert (await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": "두부"}, headers=headers)).status_code == 201
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).status_code == 204
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)) == (403, "PERMISSION_DENIED")
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 200


async def test_내보낸_직원은_받은_토큰으로도_목록을_볼_수_없다(wired):
    """C5 — 매 요청의 매장 접근 확인이 막는다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    joined = await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))
    headers = bearer(staff["access_token"])
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=headers)).status_code == 200

    member_path = f"/v1/shops/{shop_id}/members/{joined.json()['member_id']}"
    assert (await wired.api.delete(member_path, headers=bearer(owner["access_token"]))).status_code == 204
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=headers)) == (403, "NOT_A_MEMBER")


async def test_같은_번호와_질병_규칙_위반은_설계의_오류다(wired):
    """C2(순차)·C8 — 번호는 살아 있는 고객끼리 하나, 질병은 고르거나 '질병 없음' 중 하나."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    first, _ = await _register(wired, shop_id, headers)
    second, _ = await _register(wired, shop_id, headers, customer={"phone": "01011112222"})

    def post(customer=None, pet=None):
        return wired.api.post(
            f"/v1/shops/{shop_id}/customers",
            json={"customer": {**CUSTOMER, **(customer or {})}, "pet": {**PET, **(pet or {})}},
            headers=headers,
        )

    assert error_of(await post(customer={"phone": "01012345678"})) == (409, "CUSTOMER_PHONE_TAKEN")
    assert error_of(await wired.api.put(
        f"/v1/shops/{shop_id}/customers/{second}", json={**CUSTOMER, "phone": "010 1234 5678"}, headers=headers,
    )) == (409, "CUSTOMER_PHONE_TAKEN")
    assert error_of(await post(customer={"phone": "01055556666"}, pet={"no_known_conditions": False})) == (422, "PET_HEALTH_REQUIRED")
    assert error_of(await post(
        customer={"phone": "01055556666"}, pet={"conditions": [{"type_code": "allergy"}]},
    )) == (422, "PET_HEALTH_CONFLICT")
    assert error_of(await post(
        customer={"phone": "01055556666"},
        pet={"no_known_conditions": False, "conditions": [{"type_code": "flu"}]},
    )) == (422, "VALIDATION_ERROR")
    assert error_of(await post(customer={"phone": "5678"})) == (422, "VALIDATION_ERROR")
    assert error_of(await post(customer={"phone": "01055556666"}, pet={"birth_date": "2021-01-01"})) == (422, "VALIDATION_ERROR")
    listed = await _list(wired, shop_id, headers)
    assert listed["pet_count"] == 2 and len(listed["items"]) == 2   # 실패한 등록은 아무것도 남기지 않는다
    assert error_of(await wired.api.get(
        f"/v1/shops/{shop_id}/customers/lookup?phone=01055556666", headers=headers,
    )) == (404, "CUSTOMER_NOT_FOUND")
    assert {c["customer_id"] for c in listed["items"]} == {first, second}


async def test_뒷자리_초성_여러_낱말_특수_문자로_찾는다(wired):
    """7.3 — 가족 카드 단위로 찾는다. 뒷자리가 같은 고객은 모두 나온다. C10 특수 문자는 글자 그대로다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    kim, _ = await _register(wired, shop_id, headers)
    park, _ = await _register(wired, shop_id, headers, customer={"name": "박서준", "phone": "01098765678"},
                              pet={"name": "보리"})
    percent, _ = await _register(wired, shop_id, headers, customer={"name": "100%보호자", "phone": "01011112222"},
                                 pet={"name": "구름"})

    async def found(q):
        return {c["customer_id"] for c in (await _list(wired, shop_id, headers, f"?q={q}"))["items"]}

    assert await found("5678") == {kim, park}
    assert await found("ㅋㅇ") == {kim}
    assert await found("5678%20보리") == {park}
    assert await found("%25") == {percent}
    assert await found("_") == set()
    names = [c["name"] for c in (await _list(wired, shop_id, headers, "?sort=name"))["items"]]
    # 한글끼리는 가나다순이다. 한글과 숫자·영문 사이의 순서는 DB 의 정렬 규칙(개발 DB 는 en_US.utf8 — 한글이 먼저)을 따른다.
    assert [n for n in names if n != "100%보호자"] == ["김민지", "박서준"]


async def test_목록은_30_가족씩_커서로_이어진다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    for i in range(31):
        await _register(wired, shop_id, headers, customer={"name": f"보호자{i:02d}", "phone": f"0101234{i:04d}"})

    first = await _list(wired, shop_id, headers, "?sort=name")
    assert len(first["items"]) == 30 and first["pet_count"] == 31
    second = await _list(wired, shop_id, headers, f"?sort=name&cursor={first['next_cursor']}")
    assert [c["name"] for c in second["items"]] == ["보호자30"] and second["next_cursor"] is None
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/customers?cursor=broken", headers=headers)) == (422, "VALIDATION_ERROR")


async def test_질병_종류와_자기소개는_멤버에게_보인다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    types = await wired.api.get(f"/v1/shops/{shop_id}/pet-condition-types", headers=headers)
    assert [t["code"] for t in types.json()][-1] == "other" and len(types.json()) == 10
    myself = await wired.api.get(f"/v1/shops/{shop_id}/customers/myself", headers=headers)
    assert myself.status_code == 200   # /customers/{customer_id} 보다 먼저 걸린다(422 가 아니다)
    assert "/customers/lookup" in myself.json()["introduction"]


async def test_토큰_없는_요청은_고객_표면마다_401_이다(wired):
    requests = [
        ("GET", "/v1/shops/1/customers"), ("GET", "/v1/shops/1/customers/lookup?phone=01012345678"),
        ("POST", "/v1/shops/1/customers"), ("GET", "/v1/shops/1/customers/1"),
        ("PUT", "/v1/shops/1/customers/1"), ("DELETE", "/v1/shops/1/customers/1"),
        ("POST", "/v1/shops/1/customers/1/pets"), ("GET", "/v1/shops/1/pets/1"),
        ("PUT", "/v1/shops/1/pets/1"), ("DELETE", "/v1/shops/1/pets/1"),
        ("POST", "/v1/shops/1/pets/1/passed-away"), ("DELETE", "/v1/shops/1/pets/1/passed-away"),
        ("GET", "/v1/shops/1/pet-condition-types"), ("GET", "/v1/shops/1/customers/myself"),
    ]
    for method, path in requests:
        response = await wired.api.request(method, path, json={"customer": CUSTOMER, "pet": PET, **PET})
        assert error_of(response) == (401, "UNAUTHENTICATED"), f"{method} {path}"


# --- 앞 작업 검토에서 이 작업으로 넘긴 확인 거리 (C6 은 위 흐름 테스트에 이미 있어 손대지 않았다) ---

async def test_반려동물_이름을_바꾸면_검색도_새_이름을_따른다(wired):
    """PUT 으로 검색 줄을 다시 만드는지: 새 이름으로 찾고 옛 이름으로는 못 찾는다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, kong = await _register(wired, shop_id, headers)

    assert (await wired.api.put(f"/v1/shops/{shop_id}/pets/{kong}", json={**PET, "name": "몽이"}, headers=headers)).status_code == 200
    assert [c["customer_id"] for c in (await _list(wired, shop_id, headers, "?q=몽이"))["items"]] == [customer_id]
    assert (await _list(wired, shop_id, headers, "?q=콩이"))["items"] == []


async def test_무지개다리_아이가_있어도_살아있는_아이_삭제는_204다(wired):
    """살아 있는 아이 + 무지개다리 아이 가족에서 살아 있는 아이를 지워도 LAST_PET 이 아니다(무지개다리 아이도 수에 든다)."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, kong = await _register(wired, shop_id, headers)
    added = await wired.api.post(
        f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": "두부"}, headers=headers,
    )
    dubu = added.json()["pet"]["pet_id"]

    assert (await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)).status_code == 200
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{dubu}", headers=headers)).status_code == 204
