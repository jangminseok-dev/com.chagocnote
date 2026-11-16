import struct

import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.signature_image import MAX_BYTES, check_png


def _png(width=600, height=240, size=None) -> bytes:
    """머리와 IHDR 만 맞는 PNG 모양의 바이트. 서버는 그림을 풀지 않으므로 이것으로 충분하다."""
    raw = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
    return raw if size is None else raw + b"\x00" * (size - len(raw))


def test_크기_안의_PNG_는_받는다():
    check_png(_png())
    check_png(_png(width=1, height=1))


@pytest.mark.parametrize("raw", [b"", b"\xff\xd8\xff\xe0" + b"\x00" * 40, b"\x89PNG\r\n\x1a\n", _png()[:20]])
def test_PNG_가_아니면_거절한다(raw):
    with pytest.raises(CustomerInputError):
        check_png(raw)


@pytest.mark.parametrize("width,height", [(601, 240), (600, 241), (0, 240), (600, 0)])
def test_폭이나_높이가_넘으면_거절한다(width, height):
    with pytest.raises(CustomerInputError):
        check_png(_png(width=width, height=height))


def test_육만오천오백삼십육_바이트는_받고_하나_더_크면_거절한다():
    assert MAX_BYTES == 65536
    check_png(_png(size=65536))
    with pytest.raises(CustomerInputError):
        check_png(_png(size=65537))


def test_오류_글에_그림의_바이트가_없다():
    with pytest.raises(CustomerInputError) as caught:
        check_png(b"secret-bytes")
    assert "secret" not in str(caught.value)
