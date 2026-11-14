"""search 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from search.domain.errors import SearchQueryError

SEARCH_ERROR_STATUS: dict[type[Exception], int] = {
    SearchQueryError: 422,
}
