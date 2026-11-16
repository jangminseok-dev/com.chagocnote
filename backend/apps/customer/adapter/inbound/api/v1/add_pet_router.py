from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.add_pet_schema import AddPetRequestSchema
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.ports.input.add_pet_use_case import AddPetUseCase
from customer.dependencies.add_pet_provider import get_add_pet_use_case
from hub.app.dtos.shop_context import ShopContext

add_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@add_pet_router.post(
    "/{shop_id}/customers/{customer_id}/pets", response_model=PetDetailSchema, status_code=201
)
async def add_pet(
    customer_id: CustomerId,
    body: AddPetRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: AddPetUseCase = Depends(get_add_pet_use_case),
) -> PetDetailSchema:
    view = await use_case.add_pet(AddPetCommand(ctx=ctx, customer_id=customer_id, pet=body.to_input(),
                                                  intake_answer_id=body.intake_answer_id))
    return PetDetailSchema.of(view)
