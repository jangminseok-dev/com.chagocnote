from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from core.security import get_current_user_id
from guardian.app.dtos.end_guardian_link_dto import EndGuardianLinkCommand
from guardian.app.ports.input.end_guardian_link_use_case import EndGuardianLinkUseCase
from guardian.dependencies.end_guardian_link_provider import get_end_guardian_link_use_case

end_guardian_link_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])


# int32 를 넘는 값은 DB 에 닿기 전에 422 로 막는다.
@end_guardian_link_router.delete("/links/{link_id}", status_code=204)
async def end_guardian_link(
    link_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    user_id: int = Depends(get_current_user_id),
    use_case: EndGuardianLinkUseCase = Depends(get_end_guardian_link_use_case),
) -> Response:
    await use_case.end_link(EndGuardianLinkCommand(user_id=user_id, link_id=link_id))
    return Response(status_code=204)
