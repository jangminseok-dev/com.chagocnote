"""기록 검색을 실제 배선(가드·허브 포트·PG 의 trigram 과 벡터)으로 확인한다. 임베딩만 가짜다. 첫 테스트는 테넌트 격리다."""
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from hub.app.dtos.shop_context import system_context
from search.adapter.outbound.pg.search_document_pg_repository import SearchDocumentPgRepository
from search.app.ports.output.embedding_port import DIMENSIONS, Embedded, EmbeddingPort
from search.dependencies import search_wiring
from search.dependencies.indexer_provider import build_indexer
from search.domain.services.embedding_model import CURRENT_MODEL
from search.tests.helpers.builders import NOW, doc
from tests.integration.support import bearer, error_of, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")


def _axis(i: int) -> tuple[float, ...]:
    return tuple(1.0 if n == i else 0.0 for n in range(DIMENSIONS))


def _near(similarity: float, other: int = 1) -> tuple[float, ...]:
    """0번 축과 cosine 유사도가 similarity 인 길이 1 의 벡터."""
    vector = [0.0] * DIMENSIONS
    vector[0], vector[other] = similarity, math.sqrt(1 - similarity ** 2)
    return tuple(vector)


class _Embedder(EmbeddingPort):
    """정해 둔 글만 0번 축으로, 나머지는 먼 축으로 보낸다. down 이면 죽은 것이다."""

    def __init__(self, known=()):
        self.known, self.down = set(known), False

    async def embed(self, kind, texts, timeout):
        if self.down:
            return None
        return Embedded(model=CURRENT_MODEL, vectors=tuple(_axis(0) if t in self.known else _axis(300) for t in texts))


@pytest.fixture
def embedder(monkeypatch):
    fake = _Embedder()
    monkeypatch.setattr(search_wiring, "_embedder", fake)
    return fake


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


def _pet(name="콩이"):
    return {"name": name, "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
            "weight_kg": 3.2, "no_known_conditions": True}


async def _family(wired, shop_id, headers, name="김민지", phone="010-1234-5678", pet="콩이"):
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers, json={
        "customer": {"name": name, "phone": phone, "marketing_consent": False}, "pet": _pet(pet)})
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _put(wired, shop_id, *documents):
    """검색 문서를 바로 넣는다 — 대상(scope) 하나에 문서 하나씩."""
    async with async_sessionmaker(wired.engine, expire_on_commit=False)() as session:
        repository = SearchDocumentPgRepository(session)
        for d in documents:
            scope = "visit" if d.visit_id is not None else ("customer" if d.kind == "customer_memo" else "pet")
            ref_id = d.pet_id if d.kind == "condition_note" else d.source_id
            current = [x for x in await repository.list_for_target(system_context(shop_id), scope, ref_id)
                       if (x.kind, x.source_id) != (d.kind, d.source_id)]
            await repository.replace_target(system_context(shop_id), scope, ref_id, [*current, d], NOW)
        await session.commit()


async def _search(wired, shop_id, headers, q, **params):
    response = await wired.api.get(f"/v1/shops/{shop_id}/search", headers=headers, params={"q": q, **params})
    assert response.status_code == 200, response.text
    return response.json()


def _snippets(body) -> list[str]:
    return [item["snippet"] for item in body["items"]]


async def test_다른_매장의_글은_한_줄도_보이지_않는다(wired, embedder):
    """S1 — 같은 글·같은 벡터를 두 매장에 넣어도 자기 매장의 것만 나온다. 다른 매장의 경로는 403 이다."""
    a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
    b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
    a_customer, a_pet = await _family(wired, a_shop, a)
    b_customer, b_pet = await _family(wired, b_shop, b, name="이수진", pet="몽이")
    embedder.known.add("입질")
    await _put(wired, a_shop, doc("pet_memo", a_pet, customer_id=a_customer, pet_id=a_pet, body="입질이 있어요 (A)",
                                 embedding=_axis(0), model=CURRENT_MODEL))
    await _put(wired, b_shop, doc("pet_memo", b_pet, customer_id=b_customer, pet_id=b_pet, body="입질이 있어요 (B)",
                                 embedding=_axis(0), model=CURRENT_MODEL))

    assert error_of(await wired.api.get(f"/v1/shops/{b_shop}/search", headers=a, params={"q": "입질"})) == (
        403, "NOT_A_MEMBER")
    assert error_of(await wired.api.get(f"/v1/shops/{b_shop}/search/myself", headers=a)) == (403, "NOT_A_MEMBER")
    mine, theirs = await _search(wired, a_shop, a, "입질"), await _search(wired, b_shop, b, "입질")
    assert _snippets(mine) == ["입질이 있어요 (A)"] and mine["items"][0]["pet"]["name"] == "콩이"
    assert _snippets(theirs) == ["입질이 있어요 (B)"] and theirs["items"][0]["pet"]["name"] == "몽이"
    # 다른 매장의 아이로 좁혀도 그 매장의 글은 나오지 않는다.
    assert (await _search(wired, a_shop, a, "입질", pet_id=b_pet))["items"] == []


async def test_글자로도_뜻으로도_찾고_둘_다_걸린_것이_앞에_온다(wired, embedder):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    embedder.known.add("손대면 싫어하는")
    await _put(
        wired, shop_id,
        doc("care_note", 7, customer_id=customer_id, pet_id=pet_id, body="글자로만 걸려요 — 손대면 싫어하는 편"),
        doc("care_note", 8, customer_id=customer_id, pet_id=pet_id, body="뜻으로만 걸려요 — 만지면 예민해요",
            embedding=_near(0.9), model=CURRENT_MODEL),
        doc("care_note", 9, customer_id=customer_id, pet_id=pet_id, body="둘 다 걸려요 — 손대면 싫어하는 아이",
            embedding=_near(0.85), model=CURRENT_MODEL),
        doc("care_note", 10, customer_id=customer_id, pet_id=pet_id, body="뜻이 멀어요", embedding=_near(0.7),
            model=CURRENT_MODEL),
        doc("care_note", 11, customer_id=customer_id, pet_id=pet_id, body="옛 모델의 벡터예요", embedding=_axis(0),
            model="old-model"),
    )
    found = await _search(wired, shop_id, headers, "손대면 싫어하는")
    assert found["semantic"] is True
    # 글자 순위 [9, 7], 뜻 순위 [8, 9] — 둘 다 걸린 9 가 맨 앞, 각 쪽의 1등·2등이 뒤따른다. 먼 글·옛 모델은 없다.
    assert [s.split(" — ")[0] for s in _snippets(found)] == ["둘 다 걸려요", "뜻으로만 걸려요", "글자로만 걸려요"]
    first = found["items"][0]
    assert (first["kind"], first["visit_id"], first["open_pet_id"], first["date"]) == ("care_note", 9, None, "2026-11-03")
    assert first["owner"] == {"customer_id": customer_id, "name": "김민지"}
    assert first["pet"] == {"pet_id": pet_id, "name": "콩이", "photo": None}


async def test_임베딩이_죽어도_글자로_찾고_200_이다(wired, embedder):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    await _put(wired, shop_id, doc("pet_memo", pet_id, customer_id=customer_id, pet_id=pet_id, body="드라이를 무서워해요",
                                   embedding=_axis(0), model=CURRENT_MODEL))
    embedder.down = True
    found = await _search(wired, shop_id, headers, "드라이")
    assert found["semantic"] is False and _snippets(found) == ["드라이를 무서워해요"]
    assert (await _search(wired, shop_id, headers, "없는 말이에요")) == {"items": [], "semantic": False}


async def test_아이로_좁히면_그_아이의_글과_보호자_메모만_나온다(wired, embedder):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers)
    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers, json=_pet("두부"))
    dubu = added.json()["pet"]["pet_id"]
    other_customer, mong = await _family(wired, shop_id, headers, name="이수진", phone="010-9999-8888", pet="몽이")
    await _put(
        wired, shop_id,
        doc("pet_memo", kong, customer_id=customer_id, pet_id=kong, body="예민 — 콩이의 특이사항"),
        doc("care_note", 7, customer_id=customer_id, pet_id=kong, body="예민 — 콩이의 방문"),
        doc("pet_memo", dubu, customer_id=customer_id, pet_id=dubu, body="예민 — 두부의 특이사항"),
        doc("customer_memo", customer_id, customer_id=customer_id, pet_id=None, body="예민 — 보호자 메모"),
        doc("pet_memo", mong, customer_id=other_customer, pet_id=mong, body="예민 — 몽이의 특이사항"),
        doc("customer_memo", other_customer, customer_id=other_customer, pet_id=None, body="예민 — 다른 보호자 메모"),
    )
    assert len((await _search(wired, shop_id, headers, "예민"))["items"]) == 6
    narrowed = await _search(wired, shop_id, headers, "예민", pet_id=kong)
    assert sorted(s.split(" — ")[1] for s in _snippets(narrowed)) == ["보호자 메모", "콩이의 방문", "콩이의 특이사항"]
    memo = next(i for i in narrowed["items"] if i["kind"] == "customer_memo")
    assert (memo["pet"], memo["open_pet_id"], memo["visit_id"], memo["date"]) == (None, kong, None, None)
    assert memo["owner"]["name"] == "김민지"
    assert (await _search(wired, shop_id, headers, "예민", pet_id=999999))["items"] == []


async def test_같은_방문의_글은_한_줄이고_특수_글자는_글자_그대로_찾는다(wired, embedder):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    await _put(
        wired, shop_id,
        doc("care_note", 7, customer_id=customer_id, pet_id=pet_id, body="샴푸 50% 희석해서 썼어요"),
        doc("internal_note", 7, customer_id=customer_id, pet_id=pet_id, body="샴푸 50% 희석 — 내부 메모"),
        doc("care_note", 8, customer_id=customer_id, pet_id=pet_id, body="가위컷으로 정리했어요"),
    )
    found = await _search(wired, shop_id, headers, "50%")
    assert [i["visit_id"] for i in found["items"]] == [7]            # 한 방문의 두 글은 한 줄이다
    assert (await _search(wired, shop_id, headers, "%%"))["items"] == []       # '%' 는 "아무 글자"가 아니다
    assert (await _search(wired, shop_id, headers, "__"))["items"] == []


async def test_검색어가_맞지_않으면_422_이고_입력을_되돌려_주지_않는다(wired, embedder):
    shop_id, headers, _ = await _shop(wired)
    for q in ("가", "   ", "비밀스러운글" * 20):
        response = await wired.api.get(f"/v1/shops/{shop_id}/search", headers=headers, params={"q": q})
        assert error_of(response) == (422, "VALIDATION_ERROR")
        assert "비밀" not in response.text
    assert (await wired.api.get(f"/v1/shops/{shop_id}/search", headers=headers)).status_code == 422
    assert (await wired.api.get(f"/v1/shops/{shop_id}/search", params={"q": "발톱"})).status_code == 401


async def test_적은_글이_색인기를_지나_찾아지고_지우면_사라진다(wired, embedder):
    """쓰기 → 이벤트 → 줄 → 색인기 → 검색. 익명화는 색인기를 기다리지 않는다."""
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    day = datetime.now(SEOUL).date() - timedelta(days=1)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [pet_id],
        "starts_at": datetime(day.year, day.month, day.day, 11, tzinfo=SEOUL).isoformat()})
    visit_id = booked.json()["visits"][0]["visit_id"]
    await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                         json={"visit_ids": [visit_id], "action": "start"})
    saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                json={"care_note": "귀 청소할 때 예민하게 반응했어요"})
    assert saved.status_code == 200, saved.text
    embedder.known.update({"귀 만지는 걸 싫어하던 아이", "귀 청소할 때 예민하게 반응했어요"})

    async def index():
        async with async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)() as session:
            await build_indexer(session, embedder=embedder, now=lambda: datetime.now(timezone.utc)).run_once()

    assert (await _search(wired, shop_id, headers, "귀 청소"))["items"] == []          # 아직 색인 전이다
    await index()
    [by_letter] = (await _search(wired, shop_id, headers, "귀 청소"))["items"]
    assert (by_letter["visit_id"], by_letter["date"], by_letter["pet"]["name"]) == (visit_id, day.isoformat(), "콩이")
    [by_meaning] = (await _search(wired, shop_id, headers, "귀 만지는 걸 싫어하던 아이"))["items"]     # 글자는 안 겹친다
    assert by_meaning["visit_id"] == visit_id

    deleted = await wired.api.delete(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers)
    assert deleted.status_code == 204, deleted.text
    await index()
    assert (await _search(wired, shop_id, headers, "귀 청소"))["items"] == []

    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json={**_pet(), "memo": "귀 청소할 때 예민하게 반응했어요"})
    assert updated.status_code == 200, updated.text
    await index()
    [memo] = (await _search(wired, shop_id, headers, "귀 청소"))["items"]
    assert (memo["kind"], memo["open_pet_id"], memo["visit_id"]) == ("pet_memo", pet_id, None)
    await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                         json={"visit_ids": [visit_id], "action": "complete"})
    gone = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert gone.status_code == 204, gone.text
    assert (await _search(wired, shop_id, headers, "귀 청소"))["items"] == []          # 색인기를 돌리지 않았다
    assert date.today() and NOW
