"""개발용 .env · .env.auth 를 만든다. 이미 있으면 건드리지 않는다."""
from __future__ import annotations

import base64
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    env, auth_env = ROOT / ".env", ROOT / ".env.auth"
    if env.exists() or auth_env.exists():
        print(".env 또는 .env.auth 가 이미 있어서 건너뜁니다.")
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    env.write_text(
        "APP_ENV=dev\n"
        "DATABASE_URL=postgresql+asyncpg://chagoc:chagoc_dev@pgvector:5432/chagocnote\n"
        "REDIS_URL=redis://redis:6379/0\n"
        f"JWT_PUBLIC_KEY_B64={base64.b64encode(public_pem).decode()}\n"
        "S3_ENDPOINT_URL=http://minio:9000\n"
        "S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:9010\n"
        "S3_REGION=us-east-1\n"
        "S3_ACCESS_KEY=chagoc\n"
        "S3_SECRET_KEY=chagoc_dev_minio\n"
        "S3_BUCKET=chagocnote-dev\n",
        encoding="utf-8",
    )
    auth_env.write_text(
        f"JWT_PRIVATE_KEY_B64={base64.b64encode(private_pem).decode()}\n"
        f"IDENTITY_TOKEN_ENC_KEY={Fernet.generate_key().decode()}\n",
        encoding="utf-8",
    )
    print("만들었습니다:", env, auth_env)


if __name__ == "__main__":
    main()
