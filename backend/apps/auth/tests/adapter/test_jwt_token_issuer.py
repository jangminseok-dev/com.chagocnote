from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.tests.helpers.keys import make_rsa_keypair
from core.security import InvalidAccessToken, decode_access_claims, decode_access_token


def test_발급한_액세스_토큰은_공개키로_검증되고_유저_ID를_돌려준다():
    private_pem, public_pem, _ = make_rsa_keypair()
    access = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42)
    assert access.expires_in == 900
    assert decode_access_token(access.token, public_pem) == 42


def test_토큰에는_역할과_권한이_들어가지_않는다():
    private_pem, _, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42).token
    assert set(jwt.get_unverified_claims(token)) == {"sub", "jti", "typ", "iat", "exp"}


def test_만료된_토큰은_거절한다():
    private_pem, public_pem, _ = make_rsa_keypair()
    past = lambda: datetime.now(timezone.utc) - timedelta(hours=1)
    token = JwtTokenIssuer(private_pem, ttl_seconds=60, now=past).issue_access(42).token
    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, public_pem)


def test_다른_키로_서명한_토큰은_거절한다():
    private_pem, _, _ = make_rsa_keypair()
    _, other_public_pem, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42).token
    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, other_public_pem)


def test_액세스_토큰이_아닌_토큰은_거절한다():
    private_pem, public_pem, _ = make_rsa_keypair()
    forged = jwt.encode({"sub": "42", "typ": "other"}, private_pem, algorithm="RS256")
    with pytest.raises(InvalidAccessToken):
        decode_access_token(forged, public_pem)


def test_새_로그인으로_발급하면_발급_시각이_auth_time_이다():
    private_pem, public_pem, _ = make_rsa_keypair()
    fixed = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
    future_safe = lambda: fixed
    token = JwtTokenIssuer(private_pem, ttl_seconds=10**9, now=future_safe).issue_access(
        42, fresh_login=True
    ).token
    claims = jwt.get_unverified_claims(token)
    assert claims["auth_time"] == claims["iat"] == int(fixed.timestamp())
    assert decode_access_claims(token, public_pem).auth_time == int(fixed.timestamp())


def test_물려받은_auth_time_은_그대로_담긴다():
    private_pem, public_pem, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42, auth_time=1_700_000_000).token
    assert decode_access_claims(token, public_pem).auth_time == 1_700_000_000


def test_기본_발급에는_auth_time_이_없다():
    private_pem, public_pem, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42).token
    assert "auth_time" not in jwt.get_unverified_claims(token)
    assert decode_access_claims(token, public_pem).auth_time is None


def test_auth_time_이_정수가_아니면_거절한다():
    private_pem, public_pem, _ = make_rsa_keypair()
    now = int(datetime.now(timezone.utc).timestamp())
    for bad in (True, "1700000000", 1.5):
        forged = jwt.encode(
            {"sub": "42", "typ": "access", "exp": now + 60, "auth_time": bad},
            private_pem, algorithm="RS256",
        )
        with pytest.raises(InvalidAccessToken):
            decode_access_claims(forged, public_pem)


def test_수명을_주면_그_수명으로_발급하고_없으면_기본_수명이다():
    private_pem, _, _ = make_rsa_keypair()
    issuer = JwtTokenIssuer(private_pem, ttl_seconds=900)
    web = issuer.issue_access(42, ttl_seconds=1800)
    claims = jwt.get_unverified_claims(web.token)
    assert (web.expires_in, claims["exp"] - claims["iat"]) == (1800, 1800)
    app = issuer.issue_access(42)
    claims = jwt.get_unverified_claims(app.token)
    assert (app.expires_in, claims["exp"] - claims["iat"]) == (900, 900)
