"""확인할 것(③-B)의 조립 — 방문 여러 개의 사실을 한 번에 읽어 판정에 넘긴다.

미리 보기·방문 상세·하루 목록이 함께 쓴다. 방문이 몇 개든 customer 의 포트 한 번, 방문 쪽 저장소의
두 메서드 한 번씩이다(설계 C3). 판정은 도메인(`domain/services/visit_checks.py`)이 한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.visit_check_repository import HistoryAsk, NoShowAsk, VisitCheckRepository
from visit.domain.services.visit_checks import NO_SHOW_DAYS, checks_for
from visit.domain.services.visit_schedule import day_bounds, local_date
from visit.domain.value_objects.check_facts import CautionMark, Check, CheckSubject, PetFacts


@dataclass(frozen=True)
class CheckTarget:
    """확인할 것을 물을 대상 하나 — 방문 하나, 또는 아직 없는 예약의 아이 하나."""

    key: int                 # 묻는 쪽의 식별자(방문 ID 등). 답이 이 값으로 돌아온다
    customer_id: int
    pet_id: int | None       # 보호자만이면 None
    on: date                 # 방문의 날(매장 시간대) — 판정의 기준일
    before: datetime         # 이 시각보다 앞에 시작한 방문만 이력으로 센다(자기 자신과 뒤의 방문 제외)


@dataclass(frozen=True)
class ChecksRead:
    by_key: dict[int, list[Check]]      # 모든 대상의 key 가 들어 있다. 익명화한 고객의 대상은 빈 목록
    known_customers: frozenset[int]     # 살아 있는 이 매장의 고객
    known_pets: frozenset[int]          # 그 고객들의 아이로 확인된 반려동물


async def read_checks(
    ctx: ShopContext, targets: list[CheckTarget], directory: CustomerDirectoryPort,
    repo: VisitCheckRepository, today: date,
) -> ChecksRead:
    if not targets:
        return ChecksRead(by_key={}, known_customers=frozenset(), known_pets=frozenset())
    tz = ctx.timezone
    facts = await directory.care_facts(
        ctx,
        tuple(sorted({t.customer_id for t in targets})),
        tuple(sorted({t.pet_id for t in targets if t.pet_id is not None})),
        today,
    )
    history_asks = [HistoryAsk(key=t.key, pet_id=t.pet_id, before=t.before) for t in targets if t.pet_id is not None]
    last = await repo.last_completed(ctx, history_asks) if history_asks else {}
    no_shows = await repo.no_shows(ctx, [
        NoShowAsk(key=t.key, customer_id=t.customer_id,
                  since=day_bounds(t.on - timedelta(days=NO_SHOW_DAYS), tz)[0], until=t.before)
        for t in targets
    ])
    by_key: dict[int, list[Check]] = {}
    for target in targets:
        if target.customer_id not in facts.known_customers:
            by_key[target.key] = []   # 익명화한 고객의 방문에는 아무것도 내지 않는다
            continue
        fact = facts.pets.get(target.pet_id) if target.pet_id is not None else None
        caution = facts.cautions.get(target.customer_id)
        completed = last.get(target.key)
        by_key[target.key] = checks_for(CheckSubject(
            on=target.on,
            pet=None if fact is None else PetFacts(
                birth_date=fact.birth_date, birth_year=fact.birth_year,
                conditions=tuple((c.label, c.note) for c in fact.conditions),
                consent_on=fact.consent_on, passed_away=fact.passed_away,
            ),
            caution=None if caution is None else CautionMark(reason=caution.reason, until=caution.until),
            no_show_count=no_shows.get(target.key, 0),
            last_completed_on=None if completed is None else local_date(completed, tz),
        ))
    return ChecksRead(
        by_key=by_key, known_customers=facts.known_customers, known_pets=frozenset(facts.pets),
    )
