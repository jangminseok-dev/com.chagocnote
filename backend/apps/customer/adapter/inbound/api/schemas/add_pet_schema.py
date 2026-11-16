from customer.adapter.inbound.api.schemas.register_customer_schema import IntakeAnswerId, PetFieldsSchema


class AddPetRequestSchema(PetFieldsSchema):
    """기존 고객에게 반려동물을 더한다. 폼은 등록 3단계와 같다."""

    intake_answer_id: IntakeAnswerId = None   # 받은 문진표로 더할 때 — 그 답을 지운다
