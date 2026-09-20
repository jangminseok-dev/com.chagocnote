import pytest

from core.singleton.secret_manager import SecretManager, get_secret_manager


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def test_환경변수가_파일값보다_우선한다(tmp_path, monkeypatch):
    _write(tmp_path / ".env", "SAMPLE_KEY=from_file\n")
    monkeypatch.setenv("SAMPLE_KEY", "from_env")
    assert SecretManager(tmp_path).get("SAMPLE_KEY") == "from_env"


def test_환경변수가_없으면_파일값을_쓴다(tmp_path, monkeypatch):
    _write(tmp_path / ".env", "SAMPLE_KEY=from_file\n")
    monkeypatch.delenv("SAMPLE_KEY", raising=False)
    assert SecretManager(tmp_path).get("SAMPLE_KEY") == "from_file"


def test_값이_없으면_기본값을_돌려준다(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert SecretManager(tmp_path).get("MISSING_KEY", "fallback") == "fallback"


def test_require는_값이_없으면_변수명을_담아_실패한다(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MISSING_KEY"):
        SecretManager(tmp_path).require("MISSING_KEY")


def test_auth_env는_명시적으로_불러야_보인다(tmp_path, monkeypatch):
    _write(tmp_path / ".env.auth", "PRIVATE_SAMPLE=secret\n")
    monkeypatch.delenv("PRIVATE_SAMPLE", raising=False)
    manager = SecretManager(tmp_path)
    assert manager.get("PRIVATE_SAMPLE") is None
    manager.load_auth_env()
    assert manager.get("PRIVATE_SAMPLE") == "secret"


def test_get_secret_manager는_같은_인스턴스를_돌려준다():
    assert get_secret_manager() is get_secret_manager()
