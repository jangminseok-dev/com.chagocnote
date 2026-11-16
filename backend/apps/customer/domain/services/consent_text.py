"""동의서의 기본 글(⑪ 설계 3.2). 토막 셋이고 판이 있다.

글을 고치면 DEFAULT_VERSION 을 올리고 옛 글을 _BODIES 에 남긴다 — 옛 서명을 그 글자로 다시 보여야 한다.
이 글은 법률 검토를 받지 않았다. 화면·문서에서 효력을 말하지 않는다.
"""
from __future__ import annotations

from customer.domain.errors import CustomerInputError

PARTS = ("basic", "senior", "condition")   # 문서에 싣는 순서
DEFAULT_VERSION = 1

_BODIES: dict[tuple[str, int], str] = {
    ("basic", 1): (
        "미용하는 동안 피부가 붉어지거나 작은 상처가 생길 수 있어요. 조심해서 살피고, 생기면 바로 알려 드릴게요.\n"
        "털이 심하게 엉켜 있으면 아이가 아프지 않도록 짧게 밀 수 있어요.\n"
        "낯선 곳이라 아이가 긴장하거나 스트레스를 받을 수 있어요. 많이 힘들어하면 미용을 멈추거나 줄일게요.\n"
        "아이의 건강 상태와 주의할 점을 매장에 사실대로 알려 주셨어요.\n"
        "급한 일이 생기면 보호자님께 먼저 연락드리고, 닿지 않으면 가까운 동물병원으로 옮길 수 있어요."
    ),
    ("senior", 1): (
        "나이가 많은 아이는 미용이 몸에 부담이 될 수 있고, 평소에 드러나지 않던 질환이 미용 중이나 뒤에 나타날 수 있어요.\n"
        "오래 서 있기 힘들어하면 쉬어 가며 하고, 그래서 마무리가 고르지 않을 수 있어요.\n"
        "아이가 버거워 보이면 미용을 다 마치지 않고 멈출 수 있어요."
    ),
    ("condition", 1): (
        "알려 주신 지병 때문에 미용 중이나 뒤에 아이의 상태가 나빠질 수 있어요.\n"
        "미용을 해도 괜찮은지 수의사와 상의하셨는지는 보호자님이 확인해 주세요.\n"
        "미용 중에 평소와 다른 모습이 보이면 멈추고 바로 연락드릴게요."
    ),
}


def default_body(part: str, version: int = DEFAULT_VERSION) -> str:
    """기본 글. 없는 토막·판이면 KeyError — 호출하는 쪽이 저장된 값만 넘긴다."""
    return _BODIES[(part, version)]


BODY_MAX = 2000


def check_body(body: str) -> None:
    """매장이 고친 글의 규칙(⑪ 설계 3.2). 비워 둘 수 없다 — 비우려면 기본 글로 되돌린다. 오류 글에 그 글을 싣지 않는다."""
    if not body.strip():
        raise CustomerInputError("동의서의 글을 비워 둘 수 없습니다. 기본 글로 되돌려 주세요.")
    if len(body) > BODY_MAX:
        raise CustomerInputError(f"동의서의 글은 토막마다 {BODY_MAX}자까지 적을 수 있습니다.")
