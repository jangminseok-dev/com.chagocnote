from __future__ import annotations

from datetime import timedelta

RETRY_BASE_SECONDS = 30
RETRY_MAX_SECONDS = 3600
# 색인기가 집은 줄을 이만큼 뒤로 민다 — 집은 채 죽어도 그 뒤에 다른 색인기가 다시 집는다.
CLAIM_HOLD = timedelta(seconds=60)


def retry_delay(attempts: int) -> timedelta:
    """지금까지 attempts 번 미뤘을 때 다음까지의 간격 — 30초에서 두 배씩, 한 시간에서 멈춘다. 끝없이 되풀이한다."""
    return timedelta(seconds=min(RETRY_BASE_SECONDS * 2 ** min(attempts, 20), RETRY_MAX_SECONDS))
