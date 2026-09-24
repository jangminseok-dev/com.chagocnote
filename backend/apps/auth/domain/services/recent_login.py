"""최근 로그인 판정 — 계정을 빼앗는 데 쓰일 수 있는 경로(수단 연결·해제, 탈퇴) 앞의 재인증 규칙.

소셜 로그인으로 받은 토큰에만 로그인 시각(auth_time)이 있다. 갱신으로 받은 토큰에는 없어 통과하지 못한다.
결정 기록 003·004: "최근 로그인 확인"(Firebase 방식), 창은 5분이다.
"""
from __future__ import annotations

RECENT_LOGIN_SECONDS = 300
# 발급 프로세스와 검증 프로세스의 시계 차로 봐줄 수 있는 폭. 이보다 먼 미래의 로그인 시각은 믿지 않는다.
MAX_CLOCK_SKEW_SECONDS = 60


def is_recent_login(auth_time: int | None, now_epoch: int) -> bool:
    """로그인 시각이 있고, 지금으로부터 RECENT_LOGIN_SECONDS 안이며, 시계 차 허용폭보다 미래가 아니면 참."""
    if auth_time is None:
        return False
    elapsed = now_epoch - auth_time
    return -MAX_CLOCK_SKEW_SECONDS <= elapsed <= RECENT_LOGIN_SECONDS
