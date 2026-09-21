from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.grant_operator_use_case import GrantOperatorUseCase
from auth.app.use_cases.grant_operator_interactor import GrantOperatorInteractor
from auth.dependencies.auth_wiring import build_operator_repository, build_user_repository


def build_grant_operator_use_case(session: AsyncSession) -> GrantOperatorUseCase:
    """FastAPI 의존성이 아니다. 스크립트가 직접 만든 세션을 넘긴다."""
    return GrantOperatorInteractor(
        users=build_user_repository(session), operators=build_operator_repository(session)
    )
