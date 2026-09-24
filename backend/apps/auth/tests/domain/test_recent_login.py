from auth.domain.services.recent_login import MAX_CLOCK_SKEW_SECONDS, RECENT_LOGIN_SECONDS, is_recent_login

NOW = 1_700_000_000


def test_로그인_시각이_없으면_최근이_아니다():
    assert not is_recent_login(None, NOW)


def test_정확히_300초면_통과하고_301초면_아니다():
    assert is_recent_login(NOW - RECENT_LOGIN_SECONDS, NOW)
    assert not is_recent_login(NOW - RECENT_LOGIN_SECONDS - 1, NOW)


def test_미래의_로그인_시각은_시계_차_허용폭까지만_믿는다():
    assert is_recent_login(NOW + MAX_CLOCK_SKEW_SECONDS, NOW)
    assert not is_recent_login(NOW + MAX_CLOCK_SKEW_SECONDS + 1, NOW)


def test_방금_로그인은_통과한다():
    assert is_recent_login(NOW, NOW)
