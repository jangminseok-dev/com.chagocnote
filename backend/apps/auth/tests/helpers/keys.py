"""테스트에서 쓰는 임시 키. 실제 키를 저장소에 두지 않으려고 매번 새로 만든다."""
from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa


def _b64u(number: int) -> str:
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_rsa_keypair(kid: str = "test-kid") -> tuple[str, str, dict]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    numbers = key.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": kid, "alg": "RS256", "use": "sig",
           "n": _b64u(numbers.n), "e": _b64u(numbers.e)}
    return private_pem, public_pem, jwk


def make_ec_private_pem() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
