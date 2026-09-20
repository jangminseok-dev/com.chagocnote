from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.dependencies.auth_wiring import build_user_repository
from core.database import get_db


def get_get_me_use_case(db: AsyncSession = Depends(get_db)) -> GetMeUseCase:
    return GetMeInteractor(users=build_user_repository(db))
