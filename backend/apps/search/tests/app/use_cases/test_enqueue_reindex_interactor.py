import pytest

from search.app.dtos.enqueue_reindex_dto import EnqueueReindexCommand
from search.app.use_cases.enqueue_reindex_interactor import EnqueueReindexInteractor
from search.tests.helpers.builders import NOW, ctx
from search.tests.helpers.fakes import FakeQueue


def _use_case():
    queue = FakeQueue()
    return queue, EnqueueReindexInteractor(queue=queue, now=lambda: NOW)


async def test_바뀐_대상마다_줄이_하나_생긴다():
    queue, use_case = _use_case()
    await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=ctx(), scope="visit", ref_id=7))
    await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=ctx(), scope="pet", ref_id=7))
    assert queue.targets() == [(1, "visit", 7), (1, "pet", 7)]
    assert set(queue.due.values()) == {NOW}


async def test_같은_대상이_다시_바뀌면_줄은_그대로_하나이고_세대가_오른다():
    queue, use_case = _use_case()
    for _ in range(3):
        await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=ctx(), scope="visit", ref_id=7))
    [job] = queue.jobs.values()
    assert (job.generation, job.attempts) == (3, 0)


async def test_다른_매장의_같은_대상은_다른_줄이다():
    queue, use_case = _use_case()
    await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=ctx(1), scope="visit", ref_id=7))
    await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=ctx(2), scope="visit", ref_id=7))
    assert queue.targets() == [(1, "visit", 7), (2, "visit", 7)]


async def test_모르는_대상은_줄을_만들지_않고_거절한다():
    queue, use_case = _use_case()
    with pytest.raises(ValueError):
        await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=ctx(), scope="shop", ref_id=1))
    assert queue.targets() == []
