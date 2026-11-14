from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from search.domain.services.embedding_model import CURRENT_MODEL, DIMENSIONS  # noqa: F401 — 쓰는 쪽이 여기서 가져간다

QUERY_TIMEOUT = 1.5    # 검색어 하나 — 넘으면 글자 검색만으로 답한다
INDEX_TIMEOUT = 10.0   # 색인기의 한 묶음


@dataclass(frozen=True)
class Embedded:
    model: str                              # 언제나 CURRENT_MODEL — 다른 모델의 답은 "없음"으로 친다
    vectors: tuple[tuple[float, ...], ...]  # 보낸 글과 같은 순서, 하나가 DIMENSIONS 칸


class EmbeddingPort(ABC):
    """글을 벡터로 바꾼다. 구현: 임베딩 프로세스를 부르는 HTTP 어댑터. 글과 벡터를 로그에 남기지 않는다."""

    @abstractmethod
    async def embed(self, kind: str, texts: list[str], timeout: float) -> Embedded | None:
        """kind 는 "query"(찾는 말) 또는 "passage"(찾아질 글). 못 받으면 None 이다 — 시간 초과, 연결 실패, 오류
        상태, 모양·차원·개수가 다른 답, 다른 모델의 답. **던지지 않는다.** 잠금을 쥔 채 부르지 않는다."""
