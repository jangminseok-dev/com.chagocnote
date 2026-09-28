import pytest

from visit.domain.errors import (
    VisitInputError,
    VisitNotYetError,
    VisitReportSentError,
    VisitStateConflictError,
)
from visit.domain.state.visit_state import StatusChange, transition
from visit.tests.helpers.builders import TZ, kst, visit

NOW = kst(9, 23, 15)   # 오늘 오후 3시
TODAY_2PM = kst(9, 23, 14)
TOMORROW = kst(9, 24, 10)


def _apply(status, action, starts_at=TODAY_2PM, reason=None, **fields):
    return transition(visit(status=status, starts_at=starts_at, **fields), action, NOW, TZ, reason)


# (지금 상태, 행동, 취소 사유) → 결과. 표에 없는 조합은 아래에서 모두 VISIT_STATE_CONFLICT 로 확인한다.
ALLOWED = [
    ("reserved", "start", None, StatusChange("in_progress", started_at=NOW)),
    ("reserved", "complete", None, StatusChange("completed", started_at=NOW, completed_at=NOW)),
    ("reserved", "cancel", "customer_request",
     StatusChange("canceled", canceled_at=NOW, cancel_reason="customer_request")),
    ("reserved", "cancel", "shop_reason", StatusChange("canceled", canceled_at=NOW, cancel_reason="shop_reason")),
    ("reserved", "no_show", None, StatusChange("no_show")),
    ("in_progress", "revert", None, StatusChange("reserved")),
    ("completed", "revert", None, StatusChange("reserved")),
    ("canceled", "revert", None, StatusChange("reserved")),
    ("no_show", "revert", None, StatusChange("reserved")),
]


@pytest.mark.parametrize(("status", "action", "reason", "expected"), ALLOWED)
def test_허용된_전이(status, action, reason, expected):
    assert _apply(status, action, reason=reason) == expected


def test_미용_중에서_완료하면_시작_시각을_지킨다():
    started = kst(9, 23, 14, 5)
    change = _apply("in_progress", "complete", started_at=started)
    assert change == StatusChange("completed", started_at=started, completed_at=NOW)


REFUSED = [
    (status, action)
    for status in ("reserved", "in_progress", "completed", "canceled", "no_show")
    for action in ("start", "complete", "cancel", "no_show", "revert")
    if (status, action) not in {(s, a) for s, a, _, _ in ALLOWED} | {("in_progress", "complete")}
]


@pytest.mark.parametrize(("status", "action"), REFUSED)
def test_나머지_전이는_VISIT_STATE_CONFLICT_다(status, action):
    reason = "customer_request" if action == "cancel" else None
    with pytest.raises(VisitStateConflictError):
        _apply(status, action, reason=reason)


def test_거절되는_조합은_열여섯_가지다():
    """상태 다섯 × 행동 다섯 = 25칸. 허용은 9칸(예약됨 넷, 미용 중 둘, 끝난 상태 셋의 되돌리기) → 거절 16칸."""
    assert len(REFUSED) == 16


@pytest.mark.parametrize("action", ["start", "complete"])
def test_미래_날의_예약은_시작하거나_완료할_수_없다(action):
    with pytest.raises(VisitNotYetError):
        _apply("reserved", action, starts_at=TOMORROW)


@pytest.mark.parametrize("action", ["start", "complete"])
def test_지난_날의_예약은_시작하거나_완료할_수_있다(action):
    assert _apply("reserved", action, starts_at=kst(9, 20, 10)).status in ("in_progress", "completed")


def test_오늘이면_예약_시각_전이라도_시작할_수_있다():
    assert _apply("reserved", "start", starts_at=kst(9, 23, 18)).status == "in_progress"


def test_예약_시각_전에는_노쇼로_처리할_수_없다():
    with pytest.raises(VisitNotYetError):
        _apply("reserved", "no_show", starts_at=kst(9, 23, 18))


def test_예약_시각과_같으면_노쇼로_처리할_수_있다():
    assert _apply("reserved", "no_show", starts_at=NOW).status == "no_show"


def test_하루의_경계는_매장_시간대로_센다():
    """한국 시각 9/24 0시 10분은 UTC 로는 아직 9/23 이다 — 매장 시간대로 보면 내일이라 시작할 수 없다."""
    with pytest.raises(VisitNotYetError):
        _apply("reserved", "start", starts_at=kst(9, 24, 0, 10))


def test_취소에는_사유가_있어야_한다():
    with pytest.raises(VisitInputError):
        _apply("reserved", "cancel")


def test_취소가_아닌데_사유를_보내면_안_된다():
    with pytest.raises(VisitInputError):
        _apply("reserved", "start", reason="shop_reason")


def test_모르는_사유와_모르는_행동은_VALIDATION_ERROR_다():
    with pytest.raises(VisitInputError):
        _apply("reserved", "cancel", reason="weather")
    with pytest.raises(VisitInputError):
        _apply("reserved", "teleport")


def test_모든_행동은_바탕_상태의_메서드다():
    """transition() 은 행동 이름으로 상태 객체의 메서드를 찾는다 — 이름을 ACTIONS 에만 더하면 여기서 걸린다."""
    from visit.domain.state.visit_state import ACTIONS, VisitState

    assert all(callable(getattr(VisitState, action, None)) for action in ACTIONS)


def test_되돌리기만_반려동물을_가족_확인에_넘긴다():
    from visit.domain.state.visit_state import pets_to_confirm

    visits = [visit(id=1, pet_id=102), visit(id=2, pet_id=101), visit(id=3, pet_id=None)]
    assert pets_to_confirm("revert", visits) == (101, 102)
    assert all(pets_to_confirm(action, visits) == () for action in ("start", "complete", "cancel", "no_show"))


def test_알림장을_보내지_않은_완료_방문은_되돌린다():
    assert _apply("completed", "revert", has_live_report=False) == StatusChange("reserved")


def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
    with pytest.raises(VisitReportSentError):
        _apply("completed", "revert", has_live_report=True)
