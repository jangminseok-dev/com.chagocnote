from cryptography.fernet import Fernet

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher


def test_암호화한_값을_같은_키로_되돌린다():
    cipher = FernetCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt("apple-refresh-token")
    assert encrypted != "apple-refresh-token"
    assert cipher.decrypt(encrypted) == "apple-refresh-token"
