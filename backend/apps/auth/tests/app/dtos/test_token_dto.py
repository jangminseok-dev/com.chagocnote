from auth.app.dtos.token_dto import TokenPair


def test_repr에는_접근_토큰도_리프레시_토큰도_찍히지_않는다():
    tokens = TokenPair("secret-access-token", "5.secret-refresh-token", 900)
    text = repr(tokens)
    # 비교 결과를 지역 변수에 먼저 담는다. pytest 의 단언 재작성은 assert 문 안의 비교 노드까지
    # 그대로 풀어 찍으므로, 여기서 직접 비교하면 실패 출력에 원문 토큰이 찍힌다.
    access_missing = "secret-access-token" not in text
    refresh_missing = "secret-refresh-token" not in text
    assert access_missing and refresh_missing
    assert text == "TokenPair(expires_in=900)"
