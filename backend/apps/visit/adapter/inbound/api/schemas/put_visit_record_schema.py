from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StrictInt, StringConstraints, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId
from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.domain.entities.visit_record import RecordItem
from visit.domain.value_objects.record_input import MediaPlacement, RecordInput

Amount = Annotated[StrictInt, Field(ge=0, le=100_000_000)]
Note = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=1000),
    AfterValidator(lambda v: reject_control_chars(v, allow_newline=True)),
] | None


class RecordItemInput(BaseModel):
    menu_id: EntityId
    amount: Amount


class MediaPlacementInput(BaseModel):
    media_id: EntityId
    phase: Literal["before", "after"]
    sort_order: Annotated[StrictInt, Field(ge=0, le=99)]


class PutVisitRecordRequestSchema(BaseModel):
    """기록 전체 교체. 비운 칸은 지운다. version 은 기록이 없으면 보내지 않고, 있으면 읽은 버전을 보낸다.

    같은 메뉴를 두 번 적으면 422 RECORD_ITEM_DUPLICATE(도메인), 같은 미디어·같은 자리를 두 번 보내면 422 VALIDATION_ERROR.
    """

    version: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)] | None = None
    weight_kg: Annotated[Decimal, Field(ge=Decimal("0.1"), le=Decimal("999.9"), max_digits=4, decimal_places=1)] | None = None
    care_note: Note = None
    internal_note: Note = None
    payment_method: Literal["card", "cash", "transfer"] | None = None
    total_amount: Amount | None = None
    items: Annotated[list[RecordItemInput], Field(max_length=30)] = []
    media: Annotated[list[MediaPlacementInput], Field(max_length=33)] = []

    @field_validator("media")
    @classmethod
    def _media_unique(cls, media: list[MediaPlacementInput]) -> list[MediaPlacementInput]:
        if len({m.media_id for m in media}) != len(media):
            raise ValueError("같은 사진·영상을 두 번 보낼 수 없습니다.")
        if len({(m.phase, m.sort_order) for m in media}) != len(media):
            raise ValueError("같은 자리(전/후·순서)에 둘을 둘 수 없습니다.")
        return media

    def to_input(self) -> RecordInput:
        return RecordInput(
            weight_kg=self.weight_kg, care_note=self.care_note, internal_note=self.internal_note,
            payment_method=self.payment_method, total_amount=self.total_amount,
            items=tuple(RecordItem(menu_id=i.menu_id, amount=i.amount) for i in self.items),
            media=tuple(MediaPlacement(media_id=m.media_id, phase=m.phase, sort_order=m.sort_order)
                        for m in self.media),
        )
