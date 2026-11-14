from search.domain.services.snippet import SNIPPET_MAX, snippet

LONG = "가" * 50 + "발톱을 아주 짧게 깎아 달라고 하셨어요" + "나" * 60       # 132자, 걸리는 말은 50번째부터


def test_짧은_글은_그대로다():
    assert snippet("발톱 짧게", "발톱") == "발톱 짧게"
    assert snippet("가" * 80, "없는말") == "가" * 80


def test_줄바꿈과_겹친_공백은_빈칸_하나가_된다():
    assert snippet("얌전했어요.\n\n드라이할 때만\t조금  짖음", "드라이") == "얌전했어요. 드라이할 때만 조금 짖음"


def test_걸린_말이_없으면_앞에서부터_80자다():
    cut = snippet(LONG, "없는말")
    assert cut == LONG[:SNIPPET_MAX] + "…"


def test_걸린_말이_뒤에_있으면_그_자리가_들게_자른다():
    cut = snippet(LONG, "발톱을")
    assert cut.startswith("…") and cut.endswith("…")
    assert "발톱을 아주 짧게" in cut
    assert len(cut) == SNIPPET_MAX + 2
    assert cut[1:21] == "가" * 20                    # 걸린 말 앞의 20자


def test_걸린_말이_끝에_있으면_끝까지_보이고_뒤에_말줄임표가_없다():
    body = "가" * 100 + "입질 주의"
    cut = snippet(body, "입질")
    assert cut.startswith("…") and cut.endswith("입질 주의") and len(cut) == SNIPPET_MAX + 1


def test_걸린_말이_앞에_있으면_앞에_말줄임표가_없다():
    cut = snippet("입질 주의 " + "가" * 100, "입질")
    assert cut.startswith("입질 주의") and cut.endswith("…") and len(cut) == SNIPPET_MAX + 1


def test_대소문자를_가리지_않고_찾는다():
    assert "Shampoo" in snippet("가" * 100 + "Shampoo 알레르기", "shampoo")
