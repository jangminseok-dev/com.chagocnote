import base64
import string

import pytest

from core.link_token import TOKEN_LENGTH, make_token, new_public_id, read_token

KEY = b"k" * 32
OTHER_KEY = b"o" * 32
PUBLIC_ID = bytes(range(16))
ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"   # base64url 의 값 순서


def test_만들고_읽으면_같은_public_id_다():
    assert read_token(make_token(PUBLIC_ID, KEY), KEY) == PUBLIC_ID


def test_토큰은_43글자이고_주소에_그대로_쓸_수_있는_글자뿐이다():
    token = make_token(new_public_id(), KEY)
    assert TOKEN_LENGTH == 43
    assert len(token) == TOKEN_LENGTH
    assert set(token) <= set(ALPHABET)


def test_같은_public_id_와_키면_늘_같은_토큰이다():
    assert make_token(PUBLIC_ID, KEY) == make_token(PUBLIC_ID, KEY)


def test_다른_키로_만든_토큰은_읽지_않는다():
    assert read_token(make_token(PUBLIC_ID, OTHER_KEY), KEY) is None


@pytest.mark.parametrize("position", range(TOKEN_LENGTH))
def test_어느_자리든_한_글자를_바꾸면_읽지_않는다(position):
    token = make_token(PUBLIC_ID, KEY)
    for changed in ALPHABET:
        if changed != token[position]:
            assert read_token(token[:position] + changed + token[position + 1:], KEY) is None


def test_마지막_글자를_같은_바이트로_풀리는_다른_글자로_바꿔도_읽지_않는다():
    """43번째 글자는 6비트 가운데 앞 4비트만 쓴다 — 뒤 2비트만 다른 글자 셋은 같은 32바이트로 풀린다."""
    token = make_token(PUBLIC_ID, KEY)
    first = ALPHABET.index(token[-1]) // 4 * 4
    twins = [token[:-1] + ALPHABET[i] for i in range(first, first + 4) if ALPHABET[i] != token[-1]]

    assert len(twins) == 3
    for twin in twins:
        assert base64.urlsafe_b64decode(twin + "=") == base64.urlsafe_b64decode(token + "=")
        assert read_token(twin, KEY) is None


VALID = make_token(PUBLIC_ID, KEY)

STRANGE = [
    "",
    VALID[:-1],                 # 42글자
    VALID + "A",                # 44글자
    "A" * 5000,
    "가" * 43,
    "가" + VALID[1:],
    VALID + "가",                # 앞 43글자는 멀쩡하다
    " " + VALID[1:],
    VALID[:-1] + " ",
    VALID[:-1] + "\n",
    VALID + "\n",
    VALID[:20] + "\n" + VALID[21:],
    VALID[:-1] + "=",           # 패딩
    VALID + "=",
    "+" + VALID[1:],            # 주소용이 아닌 base64 글자
    "/" + VALID[1:],
    "١" * 43,                   # 아라비아 숫자(유니코드 숫자)
    None,
    43,
    VALID.encode(),
    bytearray(VALID.encode()),
    [VALID],
]


@pytest.mark.parametrize("token", STRANGE)
def test_이상한_입력은_예외_없이_None_이다(token):
    assert read_token(token, KEY) is None


def test_public_id_는_16바이트이고_만들_때마다_다르다():
    first, second = new_public_id(), new_public_id()
    assert (len(first), len(second)) == (16, 16)
    assert first != second


def test_용도가_다르면_같은_public_id_의_토큰이_서로_읽히지_않는다():
    report, form = make_token(PUBLIC_ID, KEY), make_token(PUBLIC_ID, KEY, b"form:")
    assert report != form
    assert read_token(report, KEY) == PUBLIC_ID and read_token(form, KEY, b"form:") == PUBLIC_ID
    assert read_token(report, KEY, b"form:") is None and read_token(form, KEY) is None


def test_용도를_주지_않은_토큰은_옮기기_전과_글자가_같다():
    # 옮기기 전(visit.domain.services.report_token)의 구현으로 계산해 둔 값 — 보호자에게 이미 나간 링크가 그대로 열려야 한다.
    assert make_token(PUBLIC_ID, KEY) == "AAECAwQFBgcICQoLDA0ODyyWUpTxv06d4AU2gLSYWxU"
