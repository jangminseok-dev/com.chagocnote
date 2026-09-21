from tenancy.domain.services.invite_code import (
    generate_invite_code,
    hash_invite_code,
    normalize_invite_code,
)


def test_코드는_8자리이고_헷갈리는_글자가_없다():
    for _ in range(200):
        code = generate_invite_code()
        assert len(code) == 8
        assert not set(code) & set("IO01")
        assert code.isalnum() and code == code.upper()


def test_입력한_코드는_공백과_하이픈을_빼고_대문자로_맞춘다():
    assert normalize_invite_code("  abcd-2345 ") == "ABCD2345"


def test_해시는_입력_모양이_달라도_같고_원문을_담지_않는다():
    digest = hash_invite_code("ABCD2345")
    assert digest == hash_invite_code(" abcd-2345")
    assert len(digest) == 64 and "ABCD2345" not in digest
