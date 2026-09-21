"""인증 프로세스 전용 비밀값. auth_main.py 경로에서만, 그리고 함수 안에서만 import 한다.

API 프로세스는 토큰을 발급할 수도, 제공자 토큰을 복호화할 수도, 카카오 연결을 끊을 수도 없어야 한다.
"""
from __future__ import annotations

import base64

from core.singleton.secret_manager import get_secret_manager

_m = get_secret_manager()

JWT_PRIVATE_KEY: str = base64.b64decode(_m.require("JWT_PRIVATE_KEY_B64")).decode()
# Apple 리프레시 토큰을 DB 에 넣기 전에 암호화하는 키 (Fernet).
IDENTITY_TOKEN_ENC_KEY: str = _m.require("IDENTITY_TOKEN_ENC_KEY")
# 탈퇴·해제 때 카카오 연결을 끊는 데 쓴다. 없으면 끊지 못하고 로그만 남긴다.
KAKAO_ADMIN_KEY: str = _m.get("KAKAO_ADMIN_KEY", "") or ""
