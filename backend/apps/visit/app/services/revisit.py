"""아이들의 미용 주기를 한 번에 읽고 계산한다(⑬ 설계 3.1·4.1) — 반려동물 상세·다음 예약 초안·완료 이벤트·
다시 올 때가 된 아이가 같은 길을 쓴다. 질의 수는 아이 수와 상관없이 고정이다(완료 날짜 하나)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from hub.app.dtos.family_brief import PetBrief
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.services.pet_cards import showable_pets
from visit.app.services.visit_day import start_of_day
from visit.domain.services.visit_cycle import NONE, PetCycle, bucket_of, pet_cycle
from visit.domain.value_objects.revisit import RevisitRow
from visit.domain.value_objects.revisit_settings import RevisitSettings


async def pet_cycles(
    ctx: ShopContext, pet_ids: list[int], manual: dict[int, int | None], history: VisitHistoryRepository,
    settings: RevisitSettings, today: date, including: date | None = None,
) -> dict[int, PetCycle]:
    """{반려동물 ID: 주기}. manual 은 직접 정한 값(없으면 None 이거나 빠짐). 완료 방문이 없는 아이도 든다.
    including 은 아직 완료하지 않은 "이번" 방문의 날 — 완료 시트가 누르기 전에 초안을 보일 때 넣는다."""
    rules = settings.rules()
    days = await history.completed_days(ctx, pet_ids, per_pet=rules.sample_visits)
    cycles = {}
    for pet_id in pet_ids:
        mine = days.get(pet_id, [])
        if including is not None and including not in mine:
            mine = [including, *mine][: rules.sample_visits]
        cycles[pet_id] = pet_cycle(mine, manual_weeks=manual.get(pet_id), rules=rules, today=today)
    return cycles


def shortest(cycles: list[PetCycle], settings: RevisitSettings) -> tuple[int, str]:
    """가족 묶음의 주기 — 아이들 가운데 짧은 쪽(⑬ 설계 3.4, 공통 11절). 아이가 없으면 매장의 기본 간격."""
    if not cycles:
        return settings.default_cycle_weeks, NONE
    chosen = min(cycles, key=lambda c: c.weeks)
    return chosen.weeks, chosen.source


@dataclass(frozen=True)
class RevisitBoard:
    """다시 올 때가 된 아이들(곧·지남)과 그 아이들의 요약 — 목록·수·매출 요약이 같은 거르기를 쓴다."""

    rows: list[RevisitRow]
    pets: dict[int, PetBrief]


async def revisit_board(
    ctx: ShopContext, history: VisitHistoryRepository, directory: CustomerDirectoryPort,
    settings: RevisitSettings, today: date,
) -> RevisitBoard:
    """곧·지남의 아이들(⑬ 설계 3.3·4.2) — 후보(한 해 안·앞날 예약 없음)를 넓혀 읽고 파이썬에서 거른다.
    질의 수는 아이 수와 상관없이 고정이다: 후보·요약·직접 정한 값·완료 날짜 하나씩. 무지개다리·익명화·지운 아이는
    빠진다(⑧ 의 거르기 그대로)."""
    candidates = await history.revisit_candidates(ctx, today, start_of_day(ctx, today))
    pets = await showable_pets(ctx, [c.pet_id for c in candidates], directory)
    alive = [c for c in candidates if c.pet_id in pets and not pets[c.pet_id].passed_away]
    if not alive:
        return RevisitBoard(rows=[], pets=pets)
    facts = await directory.revisit_facts(ctx, tuple(c.pet_id for c in alive))
    manual = {p: f.grooming_cycle_weeks for p, f in facts.items()}
    cycles = await pet_cycles(ctx, [c.pet_id for c in alive], manual, history, settings, today)
    rows = []
    for c in alive:
        cycle = cycles[c.pet_id]
        bucket = bucket_of(cycle, today, settings.revisit_soon_days)
        if bucket is None:
            continue
        nudged = facts[c.pet_id].revisit_nudged_on if c.pet_id in facts else None
        rows.append(RevisitRow(
            pet_id=c.pet_id, bucket=bucket, cycle=cycle, last_visit_id=c.last_visit_id,
            nudged_on=visible_nudge(nudged, c.last_day),
        ))
    # 지남은 오래 지난 순, 곧은 가까운 순 — 둘 다 다음 올 때가 이른 순이다.
    rows.sort(key=lambda r: (r.cycle.due_date, r.pet_id))
    return RevisitBoard(rows=rows, pets=pets)


def visible_nudge(nudged_on: date | None, last_visit: date | None) -> date | None:
    """안내한 날은 마지막 완료 방문보다 뒤일 때만 보인다 — 안내한 뒤 다녀갔으면 그 안내는 끝났다(목록·상세가 같다)."""
    if nudged_on is None or (last_visit is not None and nudged_on <= last_visit):
        return None
    return nudged_on


def weeks_since(last_visit: date, today: date) -> int:
    """안내 글의 {주} — 마지막 미용에서 오늘까지 주로 반올림, 최소 1."""
    return max(1, math.floor((today - last_visit).days / 7 + 0.5))
