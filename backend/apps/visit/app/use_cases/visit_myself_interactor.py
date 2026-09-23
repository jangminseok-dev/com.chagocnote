from __future__ import annotations

from visit.app.dtos.visit_myself_dto import VisitMyselfQuery, VisitMyselfResponse
from visit.app.ports.input.visit_myself_use_case import VisitMyselfUseCase
from visit.app.ports.output.visit_myself_record_port import VisitMyselfRecordPort


class VisitMyselfInteractor(VisitMyselfUseCase):
    def __init__(self, record: VisitMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: VisitMyselfQuery) -> VisitMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return VisitMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 방문(예약부터 완료까지)과 매장 일정·메뉴표를 관리합니다. "
                "경로는 모두 /v1/shops/{shop_id} 아래이고 매 요청마다 매장 소속을 확인합니다. "
                "방문 하나는 반려동물 한 마리의 방문이고, 반려동물 없이 보호자만의 방문도 있습니다. "
                "상태는 reserved → in_progress → completed 이고 canceled·no_show 로 끝날 수 있습니다. "
                "GET /visits?date= 는 하루 목록(가족 묶음 group_key, 겹침, 정리 안 된 예약), "
                "GET /visits/calendar?month=YYYY-MM 은 월 달력, GET /visits/slots?date=&duration=&at=&exclude= 는 "
                "시간 칸의 경고(overlap·closed_day·outside_hours — 막지 않음)입니다. "
                "GET /visits/defaults?pet_id= 는 그 아이의 지난 완료 방문으로 채운 메뉴·소요입니다. "
                "POST /visits 는 예약 등록(pet_ids 마다 방문 하나, 빈 목록이면 보호자만, walk_in 이면 지금 시작), "
                "GET·PUT /visits/{visit_id} 는 상세·수정, POST /visits/reschedule 는 같은 보호자의 예약을 함께 옮기기, "
                "POST /visits/transitions 는 start·complete·cancel·no_show·revert(같은 보호자의 방문만, 전부 되거나 "
                "전부 안 됨), GET /visits/{visit_id}/next-draft 는 완료한 방문의 다음 예약 초안입니다. "
                "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}, "
                "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
                "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴 수정은 shop:update(사장)가 필요합니다. "
                "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
                "다른 매장의 방문·메뉴 ID 는 404 입니다."
            ),
        )
