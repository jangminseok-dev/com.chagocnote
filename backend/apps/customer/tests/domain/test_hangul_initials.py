from customer.domain.services.hangul_initials import to_initials


def test_한글_음절을_초성으로_바꾼다():
    assert to_initials("콩이") == "ㅋㅇ"
    assert to_initials("김민지") == "ㄱㅁㅈ"


def test_된소리와_겹받침도_초성만_남는다():
    assert to_initials("꽃닭") == "ㄲㄷ"
    assert to_initials("앉은뱅이") == "ㅇㅇㅂㅇ"


def test_한글이_아닌_글자는_그대로_둔다():
    assert to_initials("Coco콩2") == "Cocoㅋ2"
    assert to_initials("콩 이") == "ㅋ ㅇ"
    assert to_initials("ㅋㅇ") == "ㅋㅇ"
    assert to_initials("") == ""
