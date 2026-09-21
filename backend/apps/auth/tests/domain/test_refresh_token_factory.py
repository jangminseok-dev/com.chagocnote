from auth.domain.services.refresh_token_factory import new_refresh_token, refresh_token_user_id


def test_토큰은_유저_ID_로_시작하고_매번_다르다():
    first, second = new_refresh_token(7), new_refresh_token(7)
    assert first.startswith("7.") and second.startswith("7.")
    assert first != second
    assert len(first.split(".", 1)[1]) >= 43


def test_토큰에서_유저_ID_를_읽는다():
    assert refresh_token_user_id(new_refresh_token(1234)) == 1234


def test_모양이_다른_토큰은_None_이다():
    for token in ("", "no-dot", ".abc", "abc.def", "-1.abc", "７.abc"):
        assert refresh_token_user_id(token) is None
