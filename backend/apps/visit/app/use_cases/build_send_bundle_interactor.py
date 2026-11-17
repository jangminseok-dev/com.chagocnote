from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.guardian_form_port import GuardianFormPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.build_send_bundle_dto import BuildSendBundleCommand, BundlePartView, SendBundleView
from visit.app.ports.input.build_send_bundle_use_case import BuildSendBundleUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_check_repository import VisitCheckRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_series_repository import VisitSeriesRepository
from visit.app.services.visit_checks import CheckTarget, read_checks
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import RESERVED
from visit.domain.services.send_bundle import build_bundle
from visit.domain.services.visit_checks import CONSENT
from visit.domain.services.visit_schedule import local_date


class BuildSendBundleInteractor(BuildSendBundleUseCase):
    """한 예약에 보호자에게 보낼 글을 한 묶음으로 조립한다(⑪ 설계 3.5) — 예약 안내와, 필요하면 동의서 링크.

    가족이 함께 잡은 예약(같은 보호자·같은 시작 시각)은 한 묶음이다. 동의서 링크는 이때 만들어져 있다 —
    사장이 따로 만들 것이 없다. 다시 불러도 같은 링크다. 방문 행은 잠그지 않는다(고객 행 → 서류 요청 행만).
    예약된 방문이 아니면 보낼 것이 없다.
    """

    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, menus: MenuRepository,
        checks: VisitCheckRepository, directory: CustomerDirectoryPort, forms: GuardianFormPort,
        shops: ShopProfilePort, now: Callable[[], datetime], series: VisitSeriesRepository,
    ) -> None:
        self._visits = visits
        self._history = history
        self._menus = menus
        self._checks = checks
        self._directory = directory
        self._forms = forms
        self._shops = shops
        self._now = now
        self._series = series

    async def build_send_bundle(self, command: BuildSendBundleCommand) -> SendBundleView:
        ctx = command.ctx
        visit = await self._visits.get(ctx, command.visit_id)
        if visit.status != RESERVED:
            return SendBundleView(parts=[])
        group = sorted(
            (v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
             if v.status == RESERVED),
            key=lambda v: v.id)
        on = local_date(visit.starts_at, ctx.timezone)
        read = await read_checks(
            ctx,
            [CheckTarget(key=v.id, customer_id=v.customer_id, pet_id=v.pet_id, on=on, before=v.starts_at)
             for v in group],
            self._directory, self._checks, local_date(self._now(), ctx.timezone))
        shop = await self._shops.public_profile(ctx.shop_id)
        if visit.customer_id not in read.known_customers or shop is None:
            return SendBundleView(parts=[])      # 익명화한 고객의 방문에는 보낼 사람이 없다
        views = await describe_visits(ctx, group, self._directory, self._menus)
        pet_names = {v.visit_id: v.pet.name for v in views if v.pet is not None}
        # 동의서는 확인할 것에 consent 가 뜬 아이에게만 보낸다 — 묻지 않는 아이에게 일을 더하지 않는다.
        asking = [v for v in group if v.pet_id is not None
                  and any(check.code == CONSENT for check in read.by_key[v.id])]
        texts = await self._forms.bundle_texts(ctx)
        link = await self._forms.consent_link(ctx, tuple(v.pet_id for v in asking), on) if asking else None
        menu_names = list(dict.fromkeys(menu.name for view in views for menu in view.menus))
        series_starts, interval_weeks = await self._series_starts(ctx, visit)
        parts = build_bundle(
            shop_name=shop.name, pet_names=list(pet_names.values()), starts_at=views[0].starts_at,
            menu_names=menu_names, reservation_text=texts.reservation, consent_text=texts.consent,
            consent_pet_names=[pet_names[v.id] for v in asking if v.id in pet_names], consent_url=None if link is None else link.url,
            series_starts=series_starts, interval_weeks=interval_weeks,
        )
        return SendBundleView(
            parts=[BundlePartView(kind=part.kind, text=part.text) for part in parts],
            created_form_id=link.form_id if link is not None and link.created else None,
        )

    async def _series_starts(self, ctx, visit) -> tuple[list[datetime], int | None]:
        """반복 묶음이면 이 예약부터의 예약됨 회차 시각들(매장 시간대)과 묶음 간격(⑭) — 접수 안내 한 통에 전부 적는다."""
        if visit.series_id is None:
            return [], None
        series = await self._series.get(ctx, visit.series_id)
        zone = ZoneInfo(ctx.timezone)
        starts = sorted({v.starts_at.astimezone(zone) for v in await self._visits.list_series(ctx, visit.series_id)
                         if v.status == RESERVED and v.starts_at >= visit.starts_at})
        return starts, series.interval_weeks
