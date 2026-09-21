import pytest
from cryptography.fernet import Fernet

from auth.adapter.outbound.gateways.fernet_cipher import DecryptionError, FernetCipher


def test_암호화한_값을_같은_키로_되돌린다():
    cipher = FernetCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt("apple-refresh-token")
    assert encrypted != "apple-refresh-token"
    assert cipher.decrypt(encrypted) == "apple-refresh-token"


def test_다른_키로_암호화된_값은_DecryptionError_다():
    encrypted = FernetCipher(Fernet.generate_key().decode()).encrypt("apple-refresh-token")
    with pytest.raises(DecryptionError):
        FernetCipher(Fernet.generate_key().decode()).decrypt(encrypted)


def test_손상된_값도_DecryptionError_다():
    with pytest.raises(DecryptionError):
        FernetCipher(Fernet.generate_key().decode()).decrypt("garbage-not-a-token")
