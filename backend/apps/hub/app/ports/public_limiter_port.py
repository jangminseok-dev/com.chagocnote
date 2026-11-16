from __future__ import annotations

from abc import ABC, abstractmethod


class PublicLimiterPort(ABC):
    """로그인 없는 공개 경로의 횟수 제한(⑤ 설계 7.1, ⑪ 설계 3.1). client 는 접속 주소다.

    알림장과 서류가 같은 규칙을 서로 다른 이름 공간으로 쓴다 — 구현은 core/public_redis_limiter.py.

    실패 수 차단은 서명이 틀린 요청에만 건다 — 서명이 맞는 토큰은 남의 실패로 막히지 않는다.
    저장소에 닿지 못하면 막지 않는다 — 1차 방어는 토큰의 크기다.
    """

    @abstractmethod
    async def allow(self, client: str) -> bool:
        """요청 하나를 세고, 1분 창의 요청 수가 한도(60) 안이면 True. 실패 수는 보지 않는다."""

    @abstractmethod
    async def note_miss(self, client: str) -> None:
        """없는 것을 찾은 요청(404)을 하나 센다."""

    @abstractmethod
    async def missed_too_much(self, client: str) -> bool:
        """10분 창의 실패 수가 한도(20)에 찼는지 읽기만 한다 — 세지 않는다."""

    @abstractmethod
    async def allow_write(self, client: str) -> bool:
        """제출 하나를 세고, 10분 창의 제출 수가 한도(10) 안이면 True. 서류 제출이 쓴다."""
