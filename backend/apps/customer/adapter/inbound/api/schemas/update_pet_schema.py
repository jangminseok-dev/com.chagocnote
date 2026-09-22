from customer.adapter.inbound.api.schemas.register_customer_schema import PetFieldsSchema


class UpdatePetRequestSchema(PetFieldsSchema):
    """반려동물 폼 전체를 보낸다(PUT). 질병 목록도 통째로 바꾼다."""
