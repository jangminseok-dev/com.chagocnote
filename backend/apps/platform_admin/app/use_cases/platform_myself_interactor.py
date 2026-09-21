from __future__ import annotations

from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery, PlatformMyselfResponse
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.app.ports.output.platform_myself_record_port import PlatformMyselfRecordPort
from platform_admin.domain.errors import NotAnOperatorError


class PlatformMyselfInteractor(PlatformMyselfUseCase):
    def __init__(self, record: PlatformMyselfRecordPort, operators: OperatorDirectoryPort) -> None:
        self._record = record
        self._operators = operators

    async def introduce_myself(self, query: PlatformMyselfQuery) -> PlatformMyselfResponse:
        if not await self._operators.is_operator(query.user_id):
            raise NotAnOperatorError("플랫폼 운영자만 쓸 수 있습니다.")
        await self._record.record(
            subject="introduce_myself", note=f"{query.name} 자기소개 조회"
        )
        return PlatformMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "플랫폼 운영자가 쓰는 표면입니다. "
                "POST /v1/platform/shops 는 매장을 개설하고 사장용 초대 코드를 돌려줍니다. "
                "코드 원문은 이 응답에서 한 번만 볼 수 있고 DB 에는 해시만 남습니다. "
                "모든 경로는 액세스 토큰과 플랫폼 운영자 지정이 필요하며 운영자가 아니면 403 입니다. "
                "운영자는 scripts/grant_operator.py 로 지정합니다. "
                "이 스포크는 자기 데이터를 갖지 않고 허브 포트(운영자 확인, 매장 개설)만 씁니다."
            ),
        )
