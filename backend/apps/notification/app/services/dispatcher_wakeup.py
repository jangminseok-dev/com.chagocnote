"""같은 프로세스에서 줄이 생기면 디스패처 루프를 바로 깨운다(설계 5.3-1). 구독자가 wake, 루프가 wait."""
from __future__ import annotations

import asyncio

_event = asyncio.Event()


def wake() -> None:
    _event.set()


async def wait(timeout: float) -> None:
    """깨우거나 timeout 초가 지나면 돌아온다. 깨어나면 이벤트를 지운다."""
    try:
        await asyncio.wait_for(_event.wait(), timeout)
    except TimeoutError:
        pass
    _event.clear()
