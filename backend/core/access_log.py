"""접근 로그에서 쿼리 문자열을 가린다.

고객 검색어(`?q=` — 이름·번호 뒷자리)와 번호 조회(`?phone=`)가 uvicorn 접근 로그에 그대로 남지 않게 한다.
경로는 남긴다. uvicorn 은 접근 로그를 `'%s - "%s %s HTTP/%s" %d'` 와 인자 튜플로 남기며 세 번째 인자가
쿼리가 붙은 경로다.
"""
from __future__ import annotations

import logging

_REDACTED = "?[가림]"


class QueryStringRedactor(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and "?" in args[2]:
            record.args = (*args[:2], args[2].split("?", 1)[0] + _REDACTED, *args[3:])
        return True


def redact_access_log_queries() -> None:
    """uvicorn 접근 로거에 가림 필터를 한 번만 단다. 진입점이 import 될 때 부른다."""
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, QueryStringRedactor) for f in logger.filters):
        logger.addFilter(QueryStringRedactor())
