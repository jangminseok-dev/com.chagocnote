"""글을 벡터로 — multilingual-e5-small 의 ONNX 판을 CPU 로 돌린다. 토치가 없다.

글과 벡터를 로그에 남기지 않는다. 이 모듈은 아무것도 찍지 않는다.
"""
from __future__ import annotations

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_DIR = "/models/e5-small/onnx"      # 이미지를 지을 때 넣는다(infra/docker/embed.Dockerfile)
DIMENSIONS = 384
MAX_TOKENS = 512
BATCH = 16
# 모델의 규칙 — 찾는 말과 찾아질 글에 서로 다른 접두어를 붙인다.
PREFIX = {"query": "query: ", "passage": "passage: "}


class Encoder:
    def __init__(self, model_dir: str) -> None:
        self._tokenizer = Tokenizer.from_file(f"{model_dir}/tokenizer.json")
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self._tokenizer.enable_padding(pad_id=self._tokenizer.token_to_id("<pad>"), pad_token="<pad>")
        self._session = ort.InferenceSession(f"{model_dir}/model.onnx", providers=["CPUExecutionProvider"])
        self._input_names = {i.name for i in self._session.get_inputs()}

    def encode(self, kind: str, texts: list[str]) -> list[list[float]]:
        """접두어 → 토큰(512 에서 자름) → 추론 → 주의 마스크로 평균 → 길이 1 로."""
        if kind not in PREFIX:
            raise ValueError("kind 는 query 또는 passage 입니다.")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH):
            vectors.extend(self._encode_batch([PREFIX[kind] + t for t in texts[start:start + BATCH]]))
        return vectors

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        encoded = self._tokenizer.encode_batch(texts)
        ids = np.array([e.ids for e in encoded], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = np.zeros_like(ids)
        hidden = self._session.run(None, feed)[0]                       # (글, 토큰, 384)
        weights = mask[:, :, None].astype(hidden.dtype)
        pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
        pooled /= np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
        return pooled.astype(float).tolist()
