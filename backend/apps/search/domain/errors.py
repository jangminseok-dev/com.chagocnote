class SearchError(Exception):
    """search 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다. 메시지에 검색어를 넣지 않는다."""

    code = "SEARCH_ERROR"


class SearchQueryError(SearchError):
    """검색어가 다듬은 뒤 2~100자가 아니다. 422 다."""

    code = "VALIDATION_ERROR"
