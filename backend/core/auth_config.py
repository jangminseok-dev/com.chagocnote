"""인증 프로세스 전용 상수 — JWT 개인키. auth_main.py 경로에서만 import 한다."""
from __future__ import annotations

import base64

from core.singleton.secret_manager import get_secret_manager

JWT_PRIVATE_KEY: str = base64.b64decode(
    get_secret_manager().require("JWT_PRIVATE_KEY_B64")
).decode()
