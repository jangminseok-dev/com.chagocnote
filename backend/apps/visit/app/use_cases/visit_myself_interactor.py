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
                "전부 안 됨), GET /visits/{visit_id}/next-draft 는 다음 예약 초안입니다(취소·노쇼한 방문은 409). "
                "POST /visit-drafts 는 카톡 글을 규칙으로 읽어 날짜·시각·보호자 후보·메뉴를 짐작한 초안입니다"
                "(저장하지 않고, 글을 남기지 않습니다). "
                "PUT /visits/{visit_id}/record 는 미용 기록의 전체 교체입니다(미용 중·완료 방문만, record:write). "
                "몸무게·케어 메모(공개)·내부 메모·결제 수단·총액(받은 돈)·실제 메뉴와 금액·사진영상(media 에서 확인한 "
                "것, 전/후와 순서)을 담고, 돈 칸은 sales:write 가 필요합니다. 기록이 있으면 읽은 version 을 보내야 하고 "
                "다르면 409 RECORD_VERSION_CONFLICT 입니다. 몸무게는 그 아이의 가장 최근 방문이면 현재 몸무게가 됩니다. "
                "POST /visits/{visit_id}/record/media {media_id, phase} 는 사진·영상 하나를 그 칸 맨 뒤에 덧붙입니다"
                "(기록이 없으면 만들고, 같은 미디어를 다시 보내도 한 번이며, 버전이 오릅니다). "
                "DELETE /visits/{visit_id}/record 는 기록 삭제입니다(record:delete, 방문은 남습니다). "
                "방문 상세는 record(기록 전체, 사진 URL 포함)와 cover(대표 사진 썸네일 — 후 → 전 → 영상 포스터), "
                "하루 목록은 항목마다 has_record·cover, 달력은 날마다 완료 방문의 cover·covers(최대 4장)를 줍니다. "
                "GET /visits/feed?cursor=&limit=&pet_id= 는 완료 방문을 완료 시각 역순으로 이어 읽는 피드입니다"
                "(카드마다 보호자·아이 요약, cover, 메뉴, 케어 메모 앞 80자, 사진 수, next_cursor 로 다음 쪽). "
                "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
                "원 단위, 비우면 가격 미정), "
                "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
                "GET·PUT /report-settings 는 알림장 설정입니다(링크 기간 link_days 7·30·null(계속), 보호자에게 보여 줄 "
                "항목 show_menus·show_shop_info·show_weight·show_amount — PUT 은 다섯 칸 전체 교체). "
                "GET /visits/{visit_id}/report 는 알림장 미리보기입니다(보호자가 볼 내용 report — 끈 항목은 null, "
                "사진영상마다 뺀 것인지 hidden — 과 링크 상태 link, 설정 settings. 기록이 없으면 409). "
                "PUT /visits/{visit_id}/report {hidden_media_ids} 는 알림장 보내기입니다(완료 방문만, record:write). "
                "뺄 사진영상 전부를 받아 저장하고 살아 있는 링크가 없으면 만들며, 다시 불러도 같은 링크입니다"
                "(응답은 미리보기와 같은 모양, 보낼 것이 없으면 422 REPORT_EMPTY). "
                "DELETE /visits/{visit_id}/report 는 링크 끊기입니다(record:write, 없으면 404 REPORT_NOT_FOUND). "
                "기록을 고치거나 사진을 덧붙여도 뺀 사진은 빠져 있습니다. "
                "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴·알림장 설정 수정은 shop:update(사장)가 필요합니다. "
                "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
                "다른 매장의 방문·메뉴 ID 는 404 입니다."
            ),
        )
