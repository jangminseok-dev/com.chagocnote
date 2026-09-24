"""media 경로 변수. bigint 를 넘는 값은 DB 에 닿기 전에 422 로 막는다(닿으면 asyncpg 오류로 500 이 된다)."""
from typing import Annotated

from fastapi import Path

MediaId = Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]
