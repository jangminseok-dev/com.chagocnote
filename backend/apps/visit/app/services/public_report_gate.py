"""공개 조회의 관문 — 토큰이 가리키는 살아 있는 링크와 영업 중인 매장. 조회와 열람 신호가 함께 쓴다.

닫힌 이유(끊음·기간 지남·매장 정지)는 가르지 않고 오류에 방문·매장의 값을 싣지 않는다(설계 6.3).
"""
from __future__ import annotations

from datetime import datetime

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.report_target_dto import ReportTarget
from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import read_token


async def open_report(
    token: str | None, client: str, now: datetime, *, link_key: bytes, reports: PublicReportRepository,
    shops: ShopProfilePort, limiter: PublicReportLimiterPort,
) -> tuple[ReportTarget, ShopProfile]:
    if not await limiter.allow(client):
        raise TooManyReportRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 열어 주세요.")
    # 서명을 확인한 public_id 로만 DB 를 읽는다. 서명이 틀리면(추측 시도) 실패 수 차단을 본다 —
    # 서명이 맞는 토큰은 실패 수 차단을 보지 않는다(남의 실패로 막히지 않는다).
    public_id = read_token(token, link_key)
    if public_id is None:
        if await limiter.missed_too_much(client):
            raise TooManyReportRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 열어 주세요.")
        await limiter.note_miss(client)
        raise ReportNotFoundError("알림장을 찾을 수 없습니다.")
    target = await reports.find(public_id)
    if target is None:
        await limiter.note_miss(client)
        raise ReportNotFoundError("알림장을 찾을 수 없습니다.")
    if not target.report.is_live(now):
        raise ReportClosedError("닫힌 알림장입니다.")
    shop = await shops.public_profile(target.shop_id)
    if shop is None or not shop.open:
        raise ReportClosedError("닫힌 알림장입니다.")
    return target, shop
