"""유저를 플랫폼 운영자로 지정한다. 여러 번 실행해도 결과가 같다.

사용: cd infra && docker compose run --rm backend python scripts/grant_operator.py <user_id>
user_id 는 GET /v1/me 응답의 id 다.
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand
from auth.dependencies.grant_operator_provider import build_grant_operator_use_case
from auth.domain.errors import UserNotFoundError
from core.config import DATABASE_URL


async def grant(user_id: int) -> None:
    engine = create_async_engine(DATABASE_URL)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await build_grant_operator_use_case(session).grant(GrantOperatorCommand(user_id=user_id))
            await session.commit()
    finally:
        await engine.dispose()


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("사용: python scripts/grant_operator.py <user_id>")
        sys.exit(2)
    user_id = int(sys.argv[1])
    try:
        asyncio.run(grant(user_id))
    except UserNotFoundError as exc:
        print(exc)
        sys.exit(1)
    print(f"유저 {user_id} 을(를) 플랫폼 운영자로 지정했습니다.")


if __name__ == "__main__":
    main()
