from __future__ import annotations

from dataclasses import dataclass

from visit.domain.entities.menu import Menu


@dataclass(frozen=True)
class MenuView:
    menu_id: int
    name: str
    default_duration_minutes: int | None
    sort_order: int
    archived: bool

    @classmethod
    def of(cls, menu: Menu) -> MenuView:
        return cls(menu_id=menu.id, name=menu.name, default_duration_minutes=menu.default_duration_minutes,
                   sort_order=menu.sort_order, archived=menu.archived)
