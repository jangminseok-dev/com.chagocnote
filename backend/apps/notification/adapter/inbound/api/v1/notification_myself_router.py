from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from notification.adapter.inbound.api.schemas.notification_myself_schema import NotificationMyselfResponseSchema
from notification.app.dtos.notification_myself_dto import NotificationMyselfQuery
from notification.app.ports.input.notification_myself_use_case import NotificationMyselfUseCase
from notification.dependencies.notification_myself_provider import get_notification_myself_use_case

notification_myself_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@notification_myself_router.get(
    "/{shop_id}/notification/myself", response_model=NotificationMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: NotificationMyselfUseCase = Depends(get_notification_myself_use_case),
) -> NotificationMyselfResponseSchema:
    result = await use_case.introduce_myself(NotificationMyselfQuery(id=7, name="알림 (notification)"))
    return NotificationMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
