from decimal import Decimal

from visit.app.services.completion_effects import sync_pet_weight
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeVisits, Journal


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    old = visits.seed(status="completed", starts_at=kst(9, 1, 14))
    latest = visits.seed(status="in_progress", starts_at=kst(9, 23, 14))
    visits.seed(status="reserved", starts_at=kst(10, 1, 14))   # 앞으로의 예약은 세지 않는다
    return journal, visits, directory, old, latest


async def test_가장_최근_시작한_방문의_몸무게만_현재_몸무게가_된다():
    journal, visits, directory, old, latest = _setup()
    await sync_pet_weight(ctx(), old, Decimal("3.0"), visits, directory)
    await sync_pet_weight(ctx(), latest, Decimal("3.4"), visits, directory)
    assert journal == [("set_pet_weight", 101, Decimal("3.4"))]


async def test_몸무게가_없거나_보호자만의_방문이면_부르지_않는다():
    journal, visits, directory, _, latest = _setup()
    await sync_pet_weight(ctx(), latest, None, visits, directory)
    alone = visits.seed(pet_id=None, status="in_progress", starts_at=kst(9, 24, 10))
    await sync_pet_weight(ctx(), alone, Decimal("3.4"), visits, directory)
    assert journal == []
