"""온보딩 요청의 칸 — 업체에만 넘기고 저장하지 않는 값이라 모양만 본다. 어긋나면 422(500 이 아니다)."""
from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

_PLAIN = r"^[^\s\x00-\x1f\x7f]+$"   # 공백·제어 문자 없는 글자열

SearchId = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=_PLAIN)]
AdminPhone = Annotated[str, StringConstraints(pattern=r"^01[0-9]{8,9}$")]    # 휴대폰, 하이픈 없이
CategoryCode = Annotated[str, StringConstraints(min_length=1, max_length=20, pattern=_PLAIN)]
SixDigits = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]          # 토큰·인증번호
SenderPhone = Annotated[str, StringConstraints(pattern=r"^[0-9]{9,11}$")]     # 발신번호 — 유선도 된다
