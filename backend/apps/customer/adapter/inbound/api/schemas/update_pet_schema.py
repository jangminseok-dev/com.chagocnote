from customer.adapter.inbound.api.schemas.register_customer_schema import IntakeAnswerId, PetFieldsSchema


class UpdatePetRequestSchema(PetFieldsSchema):
    """반려동물 폼 전체를 보낸다(PUT). 질병 목록도 통째로 바꾼다."""

    intake_answer_id: IntakeAnswerId = None   # 다시 받은 문진표를 반영할 때 — 그 답을 지운다
