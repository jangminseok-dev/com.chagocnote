"""접근 로그에 검색어·전화번호가 남지 않는다(설계 9절 C7)."""
import logging

from core.access_log import QueryStringRedactor


def _uvicorn_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 0, '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", path, "1.1", 200), None,
    )


def test_쿼리_문자열을_가리고_경로는_남긴다():
    record = _uvicorn_record("/v1/shops/1/customers/lookup?phone=01012345678")
    assert QueryStringRedactor().filter(record) is True
    message = record.getMessage()
    assert message == '127.0.0.1:5000 - "GET /v1/shops/1/customers/lookup?[가림] HTTP/1.1" 200'
    assert "01012345678" not in message


def test_쿼리가_없거나_모양이_다른_기록은_그대로_둔다():
    plain = _uvicorn_record("/v1/shops/1/customers")
    QueryStringRedactor().filter(plain)
    assert "/v1/shops/1/customers HTTP" in plain.getMessage()
    other = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 0, "시작", None, None)
    assert QueryStringRedactor().filter(other) is True and other.getMessage() == "시작"


def test_API_프로세스는_접근_로거에_가림_필터를_단다():
    import main  # noqa: F401 — import 할 때 단다

    filters = logging.getLogger("uvicorn.access").filters
    assert sum(isinstance(f, QueryStringRedactor) for f in filters) == 1


def test_기록_검색의_검색어도_가려진다():
    """⑨ — 검색어는 매장이 적어 둔 글의 한 토막일 수 있다. 한글은 주소에서 %XX 로 오지만 그것도 남기지 않는다."""
    record = _uvicorn_record("/v1/shops/3/search?q=%EA%B7%80%EB%A5%BC%20%EB%A7%8C%EC%A7%80%EB%A9%B4&pet_id=101")
    QueryStringRedactor().filter(record)
    message = record.getMessage()
    assert message == '127.0.0.1:5000 - "GET /v1/shops/3/search?[가림] HTTP/1.1" 200'
    assert "%EA" not in message and "pet_id" not in message
