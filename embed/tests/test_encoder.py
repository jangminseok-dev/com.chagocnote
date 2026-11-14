"""실제 모델로 도는 확인 — 이미지에 든 모델 파일을 읽는다(인터넷이 필요 없다)."""
from __future__ import annotations

import math

import pytest

from encoder import DIMENSIONS, MODEL_DIR, Encoder


@pytest.fixture(scope="module")
def encoder() -> Encoder:
    return Encoder(MODEL_DIR)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))   # 둘 다 길이 1


def test_벡터는_384칸이고_길이가_1이다(encoder):
    [vector] = encoder.encode("passage", ["발톱을 짧게 깎아 달라고 하셨어요"])
    assert len(vector) == DIMENSIONS
    assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, abs_tol=1e-4)


def test_같은_글은_같은_벡터다(encoder):
    a, b = encoder.encode("passage", ["목욕을 싫어해요", "목욕을 싫어해요"])
    assert _cosine(a, b) > 0.9999


def test_함께_넣어도_따로_넣어도_벡터가_같다(encoder):
    """채움(padding)이 평균에 섞이지 않는다 — 주의 마스크로 평균을 낸다."""
    short, long = "귀 청소", "미용 내내 얌전했고 드라이할 때만 조금 짖었어요. 다음에는 간식을 챙겨 두면 좋겠어요."
    [alone] = encoder.encode("passage", [short])
    together, _ = encoder.encode("passage", [short, long])
    assert _cosine(alone, together) > 0.999


def test_빈_목록이면_빈_목록이다(encoder):
    assert encoder.encode("query", []) == []


def test_아주_긴_글도_된다(encoder):
    [vector] = encoder.encode("passage", ["털이 많이 엉켜 있었어요. " * 400])
    assert len(vector) == DIMENSIONS


def test_질의와_문서는_접두어가_달라_벡터가_다르다(encoder):
    [q] = encoder.encode("query", ["귀 청소"])
    [p] = encoder.encode("passage", ["귀 청소"])
    assert _cosine(q, p) < 0.9999


def test_뜻이_가까운_글이_더_가깝다(encoder):
    [q] = encoder.encode("query", ["귀 만지는 걸 싫어하던 아이"])
    near, far = encoder.encode("passage", ["귀 청소할 때 예민하게 반응해요", "다음 달에 가위컷으로 예약 원하심"])
    assert _cosine(q, near) > _cosine(q, far)


def test_모르는_종류는_거절한다(encoder):
    with pytest.raises(ValueError):
        encoder.encode("document", ["글"])
