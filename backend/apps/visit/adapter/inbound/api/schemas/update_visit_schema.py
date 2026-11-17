from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, StrictInt, field_validator

from visit.adapter.inbound.api.schemas.build_send_bundle_schema import BundlePartSchema
from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, Memo, unique_ids
from visit.adapter.inbound.api.schemas.series_scope_schema import SeriesScopeFields
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.update_visit_dto import UpdatedVisitView


class UpdateVisitRequestSchema(SeriesScopeFields):
    """PUT — 모든 칸을 보낸다. pet_id 가 null 이면 보호자만의 방문이다."""

    starts_at: AwareDatetime
    pet_id: EntityId | None
    duration_minutes: StrictInt
    menu_ids: Annotated[list[EntityId], Field(max_length=10)]
    memo: Memo

    _menus_unique = field_validator("menu_ids")(unique_ids)


class UpdatedVisitSchema(BaseModel):
    visit: VisitSchema
    warnings: list[str]
    notice: list[BundlePartSchema]   # ⑭ 이후 전부로 시각을 바꿨을 때 보낼 글

    @classmethod
    def of(cls, view: UpdatedVisitView) -> UpdatedVisitSchema:
        return cls.model_validate(view, from_attributes=True)
