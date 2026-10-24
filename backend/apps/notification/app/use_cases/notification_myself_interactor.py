from __future__ import annotations

from notification.app.dtos.notification_myself_dto import NotificationMyselfQuery, NotificationMyselfResponse
from notification.app.ports.input.notification_myself_use_case import NotificationMyselfUseCase
from notification.app.ports.output.notification_myself_record_port import NotificationMyselfRecordPort


class NotificationMyselfInteractor(NotificationMyselfUseCase):
    def __init__(self, record: NotificationMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: NotificationMyselfQuery) -> NotificationMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return NotificationMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 카카오톡 알림톡 자동 발송(예약 접수·전날 리마인드·미용 알림장·예약 변경·취소·다음 예약 제안)과 "
                "채널 연동·설정을 관리합니다. 경로는 모두 /v1/shops/{shop_id}/notification 아래이고 매 요청마다 매장 "
                "소속을 확인합니다. 메시지 줄은 방문 이벤트가 만들고 디스패처가 보내므로 발송 API 는 없습니다. "
                "GET /notification 은 한눈에 보기입니다(channel — status none·token_requested·linked·unlinked, "
                "linked_at, sender_number, sender_verified, sms_fallback_enabled / settings — 연동 전엔 null / "
                "templates — 종류별 심사 상태와 반려 사유). "
                "온보딩은 POST /notification/channel/token {search_id, admin_phone, category_code} 로 관리자 카카오톡에 "
                "6자리 토큰을 받고(202), POST /notification/channel 에 같은 셋과 token 을 보내 연동합니다(200, 설정 기본값과 "
                "기본 5종 템플릿 등록). 틀린 토큰은 400 NOTIFICATION_TOKEN_INVALID, 먼저 토큰을 받지 않았으면 409 "
                "NOTIFICATION_CHANNEL_NOT_LINKED, 이미 연동됐으면 409 NOTIFICATION_CHANNEL_LINKED 입니다. "
                "DELETE /notification/channel 은 해제입니다(204, 템플릿 삭제·대기 줄 전부 취소, 발신번호는 남습니다). "
                "PUT /notification/settings 는 아홉 칸 전체 교체입니다(다섯 불리언, reminder_time HH:MM 08:00~21:00, "
                "next_visit_after_weeks 1~52 또는 null, next_visit_cooldown_days 1~365, sms_fallback_enabled). 끈 종류의 "
                "대기 줄은 취소되고 reminder_time 을 바꾸면 대기 중인 리마인드·다음 예약 제안의 시각을 다시 계산하며 "
                "next_visit_enabled 를 처음 켜면 그 템플릿을 등록합니다. 문자 대체는 발신번호 인증 뒤에만 켤 수 있습니다"
                "(409 NOTIFICATION_SENDER_NOT_VERIFIED). "
                "발신번호 인증은 POST /notification/sender/verification {phone}(202) 뒤 POST /notification/sender "
                "{phone, code}(200) 입니다. 토큰·인증번호 요청은 매장당 시간당 5회, 토큰·인증번호 입력은 10분에 5회까지이고 "
                "넘으면 429 NOTIFICATION_RATE_LIMITED, 업체 장애는 502 NOTIFICATION_PROVIDER_UNAVAILABLE 입니다. "
                "읽기는 소속이면 되고 연동·해제·설정·발신번호는 shop:update(사장)가 필요합니다. 시각은 매장 시간대로 "
                "돌려주고 업체 쪽 ID 와 관리자 번호는 응답에 싣지 않습니다."
            ),
        )
