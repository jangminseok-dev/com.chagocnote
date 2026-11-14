"""HTTP 겉면 — 모델 대신 가짜 인코더로 돈다."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

import app as embed_app
from encoder import DIMENSIONS, MODEL_NAME

SECRET = "귀를 만지면 무는 아이"


class _FakeEncoder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def encode(self, kind: str, texts: list[str]) -> list[list[float]]:
        self.calls.append((kind, texts))
        return [[0.0] * DIMENSIONS for _ in texts]


@pytest.fixture
def fake(monkeypatch) -> _FakeEncoder:
    encoder = _FakeEncoder()
    monkeypatch.setattr(embed_app, "get_encoder", lambda: encoder)
    return encoder


@pytest.fixture
def client(fake) -> TestClient:
    return TestClient(embed_app.app)


def test_health_는_모델_이름을_준다(client):
    assert client.get("/health").json() == {"status": "ok", "model": MODEL_NAME}


def test_embed_는_글마다_벡터_하나를_준다(client, fake):
    response = client.post("/embed", json={"kind": "passage", "texts": ["가", "나"]})
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == MODEL_NAME
    assert [len(v) for v in body["vectors"]] == [DIMENSIONS, DIMENSIONS]
    assert fake.calls == [("passage", ["가", "나"])]


@pytest.mark.parametrize("payload", [
    {"kind": "document", "texts": [SECRET]},
    {"kind": "query", "texts": []},
    {"kind": "query", "texts": [SECRET] * 65},
    {"kind": "query", "texts": [SECRET + "가" * 4000]},
    {"kind": "query"},
    {"texts": [SECRET]},
])
def test_틀린_요청은_422_이고_본문에_입력이_없다(client, fake, payload):
    response = client.post("/embed", json=payload)
    assert response.status_code == 422
    assert response.json() == {"code": "VALIDATION_ERROR", "message": "요청 형식이 올바르지 않습니다."}
    assert SECRET not in response.text
    assert fake.calls == []


def test_로그에는_건수와_시간만_남는다(client, caplog):
    with caplog.at_level(logging.DEBUG):
        client.post("/embed", json={"kind": "query", "texts": [SECRET]})
        client.post("/embed", json={"kind": "document", "texts": [SECRET]})
    assert SECRET not in caplog.text
    assert any("1건" in r.getMessage() for r in caplog.records if r.name == "embed")
