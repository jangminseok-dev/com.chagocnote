"""서명 그림의 검사(⑪ 설계 3.3). 서버는 그림을 풀지 않는다 — 머리와 폭·높이·크기만 본다."""
from __future__ import annotations

import struct

from customer.domain.errors import CustomerInputError

MAX_BYTES = 65536
MAX_WIDTH, MAX_HEIGHT = 600, 240
_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_IHDR_END = 24   # 머리 8 + 길이 4 + "IHDR" 4 + 폭 4 + 높이 4


def check_png(raw: bytes) -> None:
    """PNG 이고 600×240·65,536바이트 이하가 아니면 CustomerInputError. 오류 글에 그림의 내용을 싣지 않는다."""
    if (
        len(raw) < _IHDR_END or len(raw) > MAX_BYTES
        or raw[:8] != _SIGNATURE or raw[12:16] != b"IHDR"
    ):
        raise CustomerInputError("서명 그림이 올바르지 않습니다.")
    width, height = struct.unpack(">II", raw[16:_IHDR_END])
    if not (1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT):
        raise CustomerInputError("서명 그림이 올바르지 않습니다.")
