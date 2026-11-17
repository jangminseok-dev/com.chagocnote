"""`이 예약만 / 이후 전부`(⑭ 설계 3.7)의 잠금과 대상 — 옮기기·고치기·취소가 같은 순서를 쓴다.

고객 행(허브 포트) → 방문 행(ID 오름차순, 한 번의 `lock`) → 잠근 뒤 다시 읽은 값으로 대상을 고른다(P14).
`이후 전부` 는 같은 묶음 · 시작 시각이 이 예약 이상 · 예약됨뿐이다. 묶음이 없는 방문이면 `이 예약만` 과 같다.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.build_send_bundle_dto import BundlePartView
from visit.app.dtos.visit_view_dto import VisitView
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.entities.visit import Visit
from visit.domain.errors import (
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotFoundError,
    VisitSeriesConflictError,
)
from visit.domain.services.send_bundle import series_notice
from visit.domain.services.visit_series import conflicts_of, following_of


THIS, FOLLOWING = "this", "following"


@dataclass(frozen=True)
class Scope:
    anchors: list[Visit]       # 요청한 방문(잠근 뒤 다시 읽은 것, ID 순)
    targets: list[Visit]       # 바꿀 방문 전부 — `이 예약만` 이면 anchors 와 같다. (시작 시각, ID) 순
    series_id: int | None      # `이후 전부` 로 고른 묶음. `이 예약만`(또는 묶음 없음)이면 None


async def lock_scope(
    ctx: ShopContext, visit_ids: Sequence[int], *, following: bool, family: bool, skip_ids: frozenset[int],
    visits: VisitLookupRepository, directory: CustomerDirectoryPort, pet_ids: tuple[int, ...] = (),
) -> Scope:
    found = await visits.get_many(ctx, list(visit_ids))
    series_ids = {v.series_id for v in found}
    if not following or series_ids == {None}:
        locked = await lock_visits(ctx, list(visit_ids), visits, directory, pet_ids)
        return Scope(anchors=locked, targets=locked, series_id=None)

    if len(found) != len(set(visit_ids)):
        raise VisitNotFoundError("방문을 찾을 수 없습니다.")
    customers = {v.customer_id for v in found}
    if len(customers) != 1:
        raise VisitGroupMismatchError("같은 보호자의 방문만 한 번에 다룰 수 있습니다.")
    if len(series_ids) != 1 or len({v.starts_at for v in found}) != 1:
        raise VisitInputError("이후 전부는 한 회차에서만 할 수 있어요.")
    [series_id] = series_ids
    await directory.lock_family(ctx, customers.pop(), pet_ids)
    picked = following_of(await visits.list_series(ctx, series_id), found, family=family, skip_ids=skip_ids)
    ids = sorted({v.id for v in found} | {v.id for v in picked})
    locked = sorted(await visits.lock(ctx, ids), key=lambda v: v.id)
    anchors = [v for v in locked if v.id in set(visit_ids)]
    # 잠근 뒤 다시 읽은 값으로 한 번 더 고른다 — 그 사이 다른 요청이 시작·완료했으면 빠진다.
    targets = following_of([v for v in locked if v.series_id == series_id], anchors, family=family,
                           skip_ids=skip_ids)
    if not targets:
        raise VisitInputError("바꿀 예약이 없어요.")
    return Scope(anchors=anchors, targets=targets, series_id=series_id)


async def ensure_free(
    ctx: ShopContext, moves: Sequence[tuple[Visit, datetime]], visits: VisitLookupRepository, now: datetime,
    duration_minutes: int | None = None,
) -> None:
    """옮겨 갈 자리에 걸리는 회차가 있으면 아무것도 쓰기 전에 VISIT_SERIES_CONFLICT(P15) — 그 아이의 다른 예약,
    1년 범위 밖, 자정 넘김(duration_minutes 가 있으면 그 소요로 본다). 빼면 제자리에 서서 이어 걸리는 회차까지 싣는다."""
    if not moves:
        return
    moving = {v.id for v, _ in moves}
    occupied = [o for o in await visits.active_at(ctx, moves[0][0].customer_id, [new for _, new in moves])
                if o.id not in moving]
    conflicts = conflicts_of(moves, occupied, now, ctx.timezone, duration_minutes)
    if conflicts:
        raise VisitSeriesConflictError(conflicts, ctx.timezone)


async def notice_parts(
    ctx: ShopContext, kind: str, views: Sequence[VisitView], shops: ShopProfilePort,
) -> list[BundlePartView]:
    """`이후 전부` 뒤 보호자에게 보낼 글 하나(⑭ P13) — 바뀐(취소한) 회차를 전부 적는다. views 의 시각은 매장 시간대.
    매장 프로필을 읽지 못하면 글이 없다(보낼 묶음과 같다)."""
    shop = await shops.public_profile(ctx.shop_id)
    if shop is None or not views:
        return []
    ordered = sorted(views, key=lambda v: (v.starts_at, v.visit_id))
    part = series_notice(kind, shop_name=shop.name, pet_names=[v.pet.name for v in ordered if v.pet is not None],
                         starts=[v.starts_at for v in ordered])
    return [BundlePartView(kind=part.kind, text=part.text)]
