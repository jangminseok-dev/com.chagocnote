"""visit 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository


def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
    return SchedulePgRepository(db)


def build_menu_repository(db: AsyncSession) -> MenuRepository:
    return MenuPgRepository(db)
