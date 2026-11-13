from __future__ import annotations

from guardian.app.dtos.guardian_myself_dto import GuardianMyselfQuery, GuardianMyselfResponse
from guardian.app.ports.input.guardian_myself_use_case import GuardianMyselfUseCase
from guardian.app.ports.output.guardian_myself_record_port import GuardianMyselfRecordPort


class GuardianMyselfInteractor(GuardianMyselfUseCase):
    def __init__(self, record: GuardianMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: GuardianMyselfQuery) -> GuardianMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return GuardianMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "보호자 계정과 매장의 고객 카드를 잇는 연결을 관리합니다. 보호자는 매장의 멤버가 아니라 로그인한 "
                "계정으로 범위가 정해지고, 경로는 /v1/me/guardian 아래입니다. "
                "POST /v1/me/guardian/links (헤더 X-Report-Token) 는 받은 알림장 링크로 그 고객 카드와 계정을 "
                "잇습니다(201 {link_id}, 이미 내 연결이면 200). 열려 있는 알림장의 토큰이어야 하고(닫혔으면 410 "
                "REPORT_CLOSED, 우리가 만든 토큰이 아니면 404 REPORT_NOT_FOUND), 고객 카드 하나에는 계정 하나만 "
                "이어집니다(409 GUARDIAN_ALREADY_LINKED). 잇기는 계정당 시간당 10회까지입니다(429 "
                "GUARDIAN_RATE_LIMITED). "
                "GET /v1/me/guardian/links 는 내 연결 목록(link_id, 매장 이름, 이은 날)이고 정지·폐업한 매장의 연결은 "
                "빠집니다. DELETE /v1/me/guardian/links/{link_id} 는 보호자가 끊습니다(204, 없거나 남의 연결이면 404 "
                "GUARDIAN_LINK_NOT_FOUND). 지난 알림장과 아이들은 visit 이 같은 접두 아래에서 줍니다. "
                "매장은 GET /v1/shops/{shop_id}/customers/{customer_id}/guardian-link 로 연결 여부와 날짜만 보고"
                "(보호자가 누구인지는 주지 않습니다) DELETE 로 끊습니다(customer:write). 계정 탈퇴와 고객 익명화는 "
                "연결을 끝냅니다. 이 스포크는 전화번호·이름을 저장하지 않고 고객·반려동물을 읽지 않습니다."
            ),
        )
