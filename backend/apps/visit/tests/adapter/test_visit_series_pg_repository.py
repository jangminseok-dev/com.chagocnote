"""반복 묶음 표(⑭, 0026) — 만들고 읽는다. 다른 매장의 묶음은 없는 것이다."""
import pytest

from visit.adapter.outbound.pg.visit_series_pg_repository import VisitSeriesPgRepository
from visit.domain.errors import VisitSeriesNotFoundError
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_묶음을_만들고_읽는다(db_session):
    repo = VisitSeriesPgRepository(db_session)
    made = await repo.create(A, customer_id=5, interval_weeks=4, member_id=11)
    read = await repo.get(A, made.id)
    assert (read.id, read.shop_id, read.customer_id, read.interval_weeks, read.created_by_member_id) == (
        made.id, 1, 5, 4, 11)
    assert read.created_at is not None


async def test_다른_매장의_묶음은_VISIT_SERIES_NOT_FOUND(db_session):
    made = await VisitSeriesPgRepository(db_session).create(A, customer_id=5, interval_weeks=4, member_id=11)
    with pytest.raises(VisitSeriesNotFoundError):
        await VisitSeriesPgRepository(db_session).get(B, made.id)
