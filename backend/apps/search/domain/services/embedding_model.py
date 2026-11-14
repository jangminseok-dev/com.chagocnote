"""지금 쓰는 임베딩 모델 — 벡터는 같은 모델이 만든 것끼리만 견줄 수 있다.

모델을 바꾸면 여기와 임베딩 프로세스(embed/encoder.py)의 이름을 함께 바꾸고 scripts/reindex_search.py 를 돌린다 —
색인기가 이 이름과 다른 벡터를 다시 만든다. 차원이 달라지면 마이그레이션도 필요하다.
"""
from __future__ import annotations

CURRENT_MODEL = "intfloat/multilingual-e5-small"
DIMENSIONS = 384
