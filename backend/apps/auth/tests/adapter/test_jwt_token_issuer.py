from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.tests.helpers.keys import make_rsa_keypair
from core.security import InvalidAccessToken, decode_access_token


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
