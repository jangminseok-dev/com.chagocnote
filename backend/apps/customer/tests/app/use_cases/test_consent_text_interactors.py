"""동의서 글 읽기·고치기(⑪-B) — 판은 쌓기만 하고, 같은 글이면 쌓지 않는다."""
import pytest

from customer.app.dtos.list_consent_texts_dto import ListConsentTextsQuery
from customer.app.dtos.update_consent_text_dto import UpdateConsentTextCommand
from customer.app.services.consent_source import ConsentSource
from customer.app.use_cases.list_consent_texts_interactor import ListConsentTextsInteractor
from customer.app.use_cases.update_consent_text_interactor import UpdateConsentTextInteractor
from customer.domain.errors import CustomerInputError
from customer.domain.services.consent_text import default_body
from customer.tests.app.use_cases.test_consent_interactors import ctx


class _Texts:
    def __init__(self):
        self.rows = []        # (part, version, body)

    async def latest(self, ctx):
        found = {}
        for part, version, body in self.rows:
            found[part] = (version, body)
        return found

    async def body_of(self, ctx, part, version):
        return next((b for p, v, b in self.rows if (p, v) == (part, version)), None)

    async def append(self, ctx, part, body):
        version = 1 + sum(1 for p, _, _ in self.rows if p == part)
        self.rows.append((part, version, body))
        return version


async def _write(texts, part, body):
    return await UpdateConsentTextInteractor(texts).update_consent_text(
        UpdateConsentTextCommand(ctx=ctx(), part=part, body=body))


async def test_고치지_않은_토막은_기본_글이고_고친_토막은_그_글이다():
    texts = _Texts()
    await _write(texts, "senior", "고친 글")

    views = await ListConsentTextsInteractor(texts).list_consent_texts(ListConsentTextsQuery(ctx=ctx()))

    assert [(v.part, v.edited) for v in views] == [("basic", False), ("senior", True), ("condition", False)]
    assert views[0].body == default_body("basic") and views[1].body == "고친 글"
    assert views[1].default_body == default_body("senior")


async def test_같은_글을_다시_저장하면_판이_쌓이지_않고_되돌리면_한_판이_쌓인다():
    texts = _Texts()

    await _write(texts, "basic", "글")
    await _write(texts, "basic", "글")
    back = await _write(texts, "basic", None)
    await _write(texts, "basic", None)

    assert texts.rows == [("basic", 1, "글"), ("basic", 2, None)]
    assert (back.body, back.edited) == (default_body("basic"), False)


async def test_고친_적_없는_토막을_되돌려도_판이_쌓이지_않는다():
    texts = _Texts()
    await _write(texts, "basic", None)
    assert texts.rows == []


@pytest.mark.parametrize(("part", "body"), [("basic", " "), ("basic", "가" * 2001), ("nothing", "글")])
async def test_규칙에_어긋나면_쌓지_않는다(part, body):
    texts = _Texts()
    with pytest.raises(CustomerInputError):
        await _write(texts, part, body)
    assert texts.rows == []


async def test_지금_글은_매장이_고친_판이고_되돌린_토막은_기본_글의_판이다():
    texts = _Texts()
    await _write(texts, "senior", "첫 글")
    await _write(texts, "senior", "둘째 글")
    await _write(texts, "basic", "글")
    await _write(texts, "basic", None)

    now = await ConsentSource(texts=texts).texts(ctx())

    assert (now["senior"].source, now["senior"].version, now["senior"].body) == ("shop", 2, "둘째 글")
    assert (now["basic"].source, now["basic"].version, now["basic"].body) == ("default", 1, default_body("basic"))
    assert now["condition"].source == "default"
