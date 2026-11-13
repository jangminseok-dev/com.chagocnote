from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.guardian import ReportLinkTarget
from hub.app.ports.report_link_port import ReportLinkPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.public_context import public_context
from visit.domain.services.report_token import read_token


class ResolveReportLinkInteractor(ReportLinkPort):
    """알림장 토큰을 매장·고객으로 푼다 — 보호자가 받은 링크로 자기 계정과 고객 카드를 이을 때 쓴다(⑦ 설계 4.1).

    서명을 확인한 public_id 로만 DB 를 읽는다. 열림의 뜻은 공개 조회와 같다: 끊지 않았고 기간이 남았고 매장이
    영업 중이고 기록이 있다(익명화는 링크를 끊으므로 여기 들어 있다). 접속 주소 제한기는 쓰지 않는다 — 잇기는
    로그인한 계정 단위로 센다. 읽기만 하므로 잠그지 않는다.
    """

    def __init__(
        self, reports: PublicReportRepository, records: VisitRecordRepository, shops: ShopProfilePort,
        now: Callable[[], datetime], link_key: bytes,
    ) -> None:
        self._reports = reports
        self._records = records
        self._shops = shops
        self._now = now
        self._link_key = link_key

    async def resolve(self, token: str | None) -> ReportLinkTarget | None:
        public_id = read_token(token, self._link_key)
        if public_id is None:
            return None
        target = await self._reports.find(public_id)
        if target is None:
            return None
        return ReportLinkTarget(
            shop_id=target.shop_id, customer_id=target.visit.customer_id, live=await self._is_live(target))

    async def _is_live(self, target) -> bool:
        if not target.report.is_live(self._now()):
            return False
        shop = await self._shops.public_profile(target.shop_id)
        if shop is None or not shop.open:
            return False
        return await self._records.get(public_context(shop), target.visit.id) is not None
