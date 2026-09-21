"""인증 프로세스 전용 비밀값이 API 프로세스로 새지 않는지 확인한다."""
import subprocess
import sys
from pathlib import Path

import core.config

_BACKEND = Path(__file__).resolve().parents[1]


def test_공용_설정에는_제공자_토큰_암호화_키가_없다():
    assert not hasattr(core.config, "IDENTITY_TOKEN_ENC_KEY")


def test_API_프로세스는_인증_전용_설정을_불러오지_않는다():
    """B1 — 다른 테스트가 먼저 불러왔을 수 있으므로 새 프로세스에서 확인한다."""
    code = "import sys, main; sys.exit(1 if 'core.auth_config' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=_BACKEND)
    assert result.returncode == 0
