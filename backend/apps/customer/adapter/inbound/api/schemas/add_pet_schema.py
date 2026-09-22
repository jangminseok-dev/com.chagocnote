from customer.adapter.inbound.api.schemas.register_customer_schema import PetFieldsSchema


class AddPetRequestSchema(PetFieldsSchema):
    """기존 고객에게 반려동물을 더한다. 폼은 등록 3단계와 같다."""
