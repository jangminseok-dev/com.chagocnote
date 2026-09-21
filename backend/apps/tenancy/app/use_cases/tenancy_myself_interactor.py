from __future__ import annotations

from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery, TenancyMyselfResponse
from tenancy.app.ports.input.tenancy_myself_use_case import TenancyMyselfUseCase
from tenancy.app.ports.output.tenancy_myself_record_port import TenancyMyselfRecordPort


class TenancyMyselfInteractor(TenancyMyselfUseCase):
    def __init__(self, record: TenancyMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: TenancyMyselfQuery) -> TenancyMyselfResponse:
        await self._record.record(
            subject="introduce_myself", note=f"{query.name} 자기소개 조회"
        )
        return TenancyMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장과 매장별 역할·권한, 소속, 초대를 관리합니다. "
                "플랫폼 운영자가 매장을 개설하면 사장용 초대 코드가 나오고, "
                "POST /v1/invites/accept 에 코드를 넣은 유저가 그 매장의 멤버가 됩니다. "
                "GET /v1/shops/{shop_id}/members 는 멤버 목록을, "
                "POST /v1/shops/{shop_id}/invites 는 직원용 초대 코드를 돌려줍니다. "
                "PATCH·DELETE /v1/shops/{shop_id}/members/{member_id} 는 역할 변경과 내보내기입니다. "
                "GET·PUT /v1/shops/{shop_id}/settings 는 매장 정보 조회와 수정입니다. "
                "매장 경로는 매 요청마다 소속과 권한을 DB 에서 확인하며 소속이 아니면 403 입니다. "
                "초대 코드는 8자리이고 해시만 저장하며 7일 뒤 만료되고 입력 시도는 유저당 분당 5회입니다. "
                "매장에는 사장이 항상 한 명 이상 있어야 합니다."
            ),
        )
