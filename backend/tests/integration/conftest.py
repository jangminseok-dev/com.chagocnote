"""두 프로세스의 실제 앱 객체에 붙는 픽스처 — 프로바이더·DB 커밋·Redis 까지 실제 배선을 통과한다."""
from __future__ import annotations

import base64

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.tests.helpers.keys import make_rsa_keypair
from tests.integration.support import Wired


@pytest.fixture
async def wired(db_engine, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    # auth_main 은 import 시점에 개인키를 요구한다. 개발용 실제 키 대신 매번 새로 만든 키를 넣는다.
    monkeypatch.setenv("JWT_PRIVATE_KEY_B64", base64.b64encode(private_pem.encode()).decode())
    enc_key = Fernet.generate_key().decode()
    monkeypatch.setenv("IDENTITY_TOKEN_ENC_KEY", enc_key)

    import core.auth_config
    import core.config
    import core.database
    import core.redis
    import core.security
    from auth.dependencies import auth_wiring

    monkeypatch.setattr(core.auth_config, "JWT_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(core.auth_config, "IDENTITY_TOKEN_ENC_KEY", enc_key)
    monkeypatch.setattr(core.auth_config, "KAKAO_ADMIN_KEY", "")
    monkeypatch.setattr(core.security, "JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(core.config, "APP_ENV", "dev")
    monkeypatch.setattr(auth_wiring, "_resolver", None)  # APP_ENV 를 바꿨으니 제공자 목록을 다시 만들게 한다
    monkeypatch.setattr(core.database, "engine", db_engine)
    monkeypatch.setattr(
        core.database,
        "_session_factory",
        async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False),
    )
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    redis = from_url(core.config.REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await redis.flushdb()
    monkeypatch.setattr(core.redis, "_client", redis)

    import auth_main
    import main

    async with (
        AsyncClient(transport=ASGITransport(app=auth_main.app), base_url="http://auth") as auth,
        AsyncClient(transport=ASGITransport(app=main.app), base_url="http://api") as api,
    ):
        yield Wired(auth=auth, api=api, engine=db_engine)
    await redis.flushdb()
    await redis.aclose()
