from __future__ import annotations

from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.guardian_report_dto import GuardianWeightView, ReadGuardianWeightsQuery
from visit.app.ports.input.read_guardian_weights_use_case import ReadGuardianWeightsUseCase
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.services.guardian_scope import guardian_scope
from visit.domain.errors import ReportNotFoundError
from visit.domain.services.visit_schedule import local_date

LIMIT = 24


class ReadGuardianWeightsInteractor(ReadGuardianWeightsUseCase):
    """아이의 몸무게 변화(⑫ 설계 3.3) — 보호자가 볼 수 있는 알림장에 실린 몸무게만, 오래된 것부터 최근 24개.
    매장이 알림장의 몸무게를 지금 껐으면 비어 있다(한 장이 설정을 읽는 때를 따르는 것과 같다). 풀이 없이 숫자만.
    그 연결에서 알림장을 받은 적 없는 아이는 404 — 아이가 있는지를 드러내지 않는다."""

    def __init__(self, reports: GuardianReportRepository, settings: ReportSettingsRepository, shops: ShopProfilePort) -> None:
        self._reports = reports
        self._settings = settings
        self._shops = shops

    async def read_weights(self, query: ReadGuardianWeightsQuery) -> list[GuardianWeightView]:
        scope = await guardian_scope(query.guardian, self._shops)
        if scope is None:
            return []
        ctx, _ = scope
        customer_id = query.guardian.customer_id
        if query.pet_id not in await self._reports.pet_ids_with_reports(ctx, customer_id):
            raise ReportNotFoundError("기록을 찾을 수 없습니다.")
        if not (await self._settings.get(ctx)).show_weight:
            return []
        found = await self._reports.weights(ctx, customer_id, query.pet_id, LIMIT)
        return [GuardianWeightView(visit_date=local_date(at, ctx.timezone), weight_kg=kg) for at, kg in reversed(found)]
