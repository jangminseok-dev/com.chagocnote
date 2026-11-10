"""가족 묶음 줄의 아이 빼기·더하기 — variables 의 pet_ids·pet_visits 만 다루는 순수 규칙(설계 2026-11-10 3.1)."""
from notification.domain.services.family_group import pet_ids_of, pet_visits_of, with_pets, without_pets
from notification.tests.helpers.builders import message

ROW = dict(visit_id=7, pet_id=101, variables={"starts_at": "S", "pet_ids": "101,102", "pet_visits": "101:7,102:8"})


def test_pet_ids_는_칸이_없으면_자기_아이_하나다():
    assert pet_ids_of({"pet_ids": "101,102"}, 101) == [101, 102]
    assert pet_ids_of({"pet_ids": ""}, 101) == []
    assert pet_ids_of({}, 101) == [101]
    assert pet_ids_of({}, None) == []


def test_pet_visits_는_아이별_방문이고_칸이_없거나_비면_빈_사전이다():
    assert pet_visits_of({"pet_visits": "101:7,102:8"}) == {101: 7, 102: 8}
    assert pet_visits_of({"pet_visits": ""}) == {}
    assert pet_visits_of({}) == {}


def test_다른_아이가_빠지면_이름만_빠지고_줄은_제자리다():
    edit = without_pets(message(**ROW), {102})
    assert (edit.variables["pet_ids"], edit.variables["pet_visits"]) == ("101", "101:7")
    assert (edit.visit_id, edit.pet_id, edit.emptied, edit.stranded) == (7, 101, False, False)
    assert edit.variables["starts_at"] == "S"


def test_줄이_달린_아이가_빠지면_남은_아이의_방문으로_옮긴다():
    edit = without_pets(message(**ROW), {101})
    assert (edit.variables["pet_ids"], edit.visit_id, edit.pet_id, edit.stranded) == ("102", 8, 102, False)


def test_옮길_방문을_모르면_제자리에_두고_stranded_다():
    edit = without_pets(message(visit_id=7, pet_id=101, variables={"pet_ids": "101,102"}), {101})
    assert (edit.variables["pet_ids"], edit.visit_id, edit.pet_id, edit.stranded) == ("102", 7, 101, True)


def test_모두_빠지면_emptied_다():
    assert without_pets(message(**ROW), {101, 102}).emptied is True


def test_세_마리에서_둘이_빠지면_남은_하나로_옮긴다():
    row = message(visit_id=7, pet_id=101, variables={"pet_ids": "101,102,103", "pet_visits": "101:7,102:8,103:9"})
    edit = without_pets(row, {101, 102})
    assert (edit.variables["pet_ids"], edit.variables["pet_visits"], edit.visit_id, edit.pet_id) == (
        "103", "103:9", 9, 103)


def test_겹치는_아이가_없으면_None_이다():
    assert without_pets(message(**ROW), {999}) is None


def test_pet_ids_칸이_없는_옛_줄은_자기_아이_하나로_본다():
    assert without_pets(message(visit_id=7, pet_id=101, variables={}), {101}).emptied is True
    assert without_pets(message(visit_id=7, pet_id=None, variables={}), {101}) is None


def test_더하면_오름차순으로_들어가고_짝을_채운다():
    row = message(visit_id=8, pet_id=102, variables={"pet_ids": "102", "pet_visits": "102:8"})
    assert with_pets(row, {101}, 101, 7) == {"pet_ids": "101,102", "pet_visits": "101:7,102:8"}


def test_이미_있는_아이는_짝만_채운다():
    row = message(visit_id=7, pet_id=101, variables={"pet_ids": "101,102", "pet_visits": "101:7"})
    assert with_pets(row, {101, 102}, 102, 8)["pet_visits"] == "101:7,102:8"


def test_더할_때_다른_칸은_그대로다():
    row = message(visit_id=7, pet_id=101, variables={"starts_at": "S", "pet_ids": "101", "pet_visits": "101:7"})
    assert with_pets(row, {102}, 102, 8) == {"starts_at": "S", "pet_ids": "101,102", "pet_visits": "101:7,102:8"}


def test_바뀔_것이_없으면_None_이다():
    assert with_pets(message(**ROW), {101, 102}, 102, 8) is None
    assert with_pets(message(**ROW), (), None, 9) is None
