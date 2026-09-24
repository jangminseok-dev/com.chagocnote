from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.menu_view_dto import MenuView


class MenuSchema(BaseModel):
    menu_id: int
    name: str
    default_duration_minutes: int | None   # None 이면 매장 기본 소요
    sort_order: int
    archived: bool
    price: int | None   # None 이면 가격 미정

    @classmethod
    def of(cls, view: MenuView) -> MenuSchema:
        return cls(menu_id=view.menu_id, name=view.name,
                   default_duration_minutes=view.default_duration_minutes, sort_order=view.sort_order,
                   archived=view.archived, price=view.price)


class MenuListSchema(BaseModel):
    items: list[MenuSchema]
