from customer.domain.services.search_terms import SearchWord, build_search_entry, parse_query


def test_이름_초성_전화_숫자로_검색_문자열을_만든다():
    entry = build_search_entry("김민지", "01012345678", ["콩이", "두부"])
    assert entry.terms == "김민지 ㄱㅁㅈ 콩이 ㅋㅇ 두부 ㄷㅂ 01012345678"
    assert (entry.phone_last4, entry.sort_name) == ("5678", "김민지")


def test_영문_이름은_초성이_같아서_한_번만_넣는다():
    entry = build_search_entry("Mina", "01012345678", ["Coco"])
    assert entry.terms == "Mina Coco 01012345678"


def test_반려동물이_없어도_만든다():
    assert build_search_entry("콩이 보호자", "0212345678", []).terms == "콩이 보호자 ㅋㅇ ㅂㅎㅈ 0212345678"


def test_숫자_네_자리_이하는_뒷자리_그_이상은_전체_번호_검색이다():
    assert parse_query("5678") == (SearchWord("last4", "5678"),)
    assert parse_query("56") == (SearchWord("last4", "56"),)
    assert parse_query("1234-5678") == (SearchWord("phone", "12345678"),)
    assert parse_query("01012") == (SearchWord("phone", "01012"),)


def test_여러_낱말로_나눈다():
    assert parse_query("  5678  콩 ") == (SearchWord("last4", "5678"), SearchWord("text", "콩"))
    assert parse_query("ㅋㅇ") == (SearchWord("text", "ㅋㅇ"),)


def test_빈_검색어는_낱말이_없다():
    assert parse_query(None) == ()
    assert parse_query("   ") == ()
    assert parse_query("-") == (SearchWord("text", "-"),)
