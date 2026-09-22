from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.customer_myself_schema import CustomerMyselfResponseSchema
from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery
from customer.app.ports.input.customer_myself_use_case import CustomerMyselfUseCase
from customer.dependencies.customer_myself_provider import get_customer_myself_use_case

customer_myself_router = APIRouter(prefix="/v1/shops", tags=["customers"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@customer_myself_router.get(
    "/{shop_id}/customers/myself", response_model=CustomerMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: CustomerMyselfUseCase = Depends(get_customer_myself_use_case),
) -> CustomerMyselfResponseSchema:
    result = await use_case.introduce_myself(CustomerMyselfQuery(id=4, name="고객 (customer)"))
    return CustomerMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
