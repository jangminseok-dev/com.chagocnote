"""공개 조회의 횟수를 셀 접속 주소(설계 7.1, 7.5 R17).

백엔드에 붙는 상대는 보호자가 아니라 웹 서버다. 웹 서버가 알려 준 보호자의 주소는 나눈 비밀값이 맞을 때만 믿는다.
비밀값이 없는 요청도 받는다 — 연결된 주소로 셀 뿐이다.
"""
from __future__ import annotations

import hmac

from fastapi import Request

from core.config import REPORT_WEB_SECRET


def get_public_client(request: Request) -> str:
    secret = request.headers.get("x-report-web-secret", "")
    forwarded = request.headers.get("x-report-client-ip", "")
    # 설정이 비어 있으면 빈 비밀값끼리 같아지지 않게 늘 믿지 않는다.
    if REPORT_WEB_SECRET and forwarded and hmac.compare_digest(secret.encode(), REPORT_WEB_SECRET.encode()):
        return forwarded
    return request.client.host if request.client else "unknown"
