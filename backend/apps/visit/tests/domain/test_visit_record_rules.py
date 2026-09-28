from dataclasses import replace
from decimal import Decimal

import pytest

from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord
from visit.domain.errors import (
    RecordItemDuplicateError,
    RecordMediaLimitError,
    RecordVersionConflictError,
    RecordWeightWithoutPetError,
    VisitNoRecordYetError,
)
from visit.domain.services.visit_record_rules import (
    append_media,
    check_input,
    check_media_limits,
    check_recordable,
    check_version,
    cover_media_id,
    next_version,
)
from visit.domain.value_objects.record_input import RecordInput
from visit.tests.helpers.builders import visit


def _input(weight=None, items=(), **fields):
    return RecordInput(weight_kg=weight, care_note=None, internal_note=None, payment_method=None,
                       total_amount=None, items=tuple(items), media=(), **fields)


def _record(version=1, media=()):
    return VisitRecord(visit_id=1, weight_kg=None, care_note=None, internal_note=None, payment_method=None,
                       total_amount=None, items=(), media=tuple(media), version=version, created_by_member_id=11,
                       updated_by_member_id=11)


def _m(media_id, kind="photo", phase="after", order=0):
    return RecordMedia(media_id=media_id, kind=kind, phase=phase, sort_order=order)


@pytest.mark.parametrize("status", ["in_progress", "completed"])
def test_미용을_시작한_방문에는_기록을_쓴다(status):
    check_recordable(visit(status=status))


@pytest.mark.parametrize("status", ["reserved", "canceled", "no_show"])
def test_시작하지_않은_방문에는_VISIT_NO_RECORD_YET(status):
    with pytest.raises(VisitNoRecordYetError):
        check_recordable(visit(status=status))


def test_보호자만의_방문에는_몸무게가_없다():
    check_input(visit(pet_id=None), _input())
    with pytest.raises(RecordWeightWithoutPetError):
        check_input(visit(pet_id=None), _input(weight=Decimal("3.2")))


def test_같은_메뉴를_두_번_적으면_RECORD_ITEM_DUPLICATE():
    with pytest.raises(RecordItemDuplicateError):
        check_input(visit(), _input(items=[RecordItem(1, 30000), RecordItem(1, 5000)]))


def test_돈_칸은_총액_항목_결제_수단이다():
    assert not _input().has_money
    assert _input(items=[RecordItem(1, 0)]).has_money
    assert RecordInput(None, None, None, "cash", None, (), ()).has_money
    assert RecordInput(None, None, None, None, 0, (), ()).has_money


def test_사진_30장_영상_3편까지():
    check_media_limits(["photo"] * 30 + ["video"] * 3)
    for kinds in (["photo"] * 31, ["video"] * 4):
        with pytest.raises(RecordMediaLimitError):
            check_media_limits(kinds)


def test_버전은_없을_때_보내지_않고_있을_때_지금_값을_보낸다():
    check_version(None, None)
    check_version(_record(3), 3)
    for current, requested in ((None, 1), (_record(3), None), (_record(3), 2)):
        with pytest.raises(RecordVersionConflictError):
            check_version(current, requested)
    assert (next_version(None), next_version(_record(3))) == (1, 4)


def test_대표_사진은_후_사진_첫_장_그다음_전_사진_그다음_영상이다():
    assert cover_media_id([_m(1, phase="before"), _m(2, order=3), _m(3, order=1), _m(9, "video", order=0)]) == 3
    assert cover_media_id([_m(1, phase="before", order=2), _m(4, phase="before", order=0), _m(9, "video")]) == 4
    assert cover_media_id([_m(8, "video", "before", 0), _m(9, "video", "after", 5)]) == 9
    assert cover_media_id([]) is None


def test_덧붙이면_그_칸의_맨_뒤이고_그_칸은_순서를_지킨_채_0부터_다시_매긴다():
    media = [_m(1, phase="before", order=3), _m(2, phase="before", order=90), _m(3, phase="after", order=5)]
    assert append_media(media, 9, "video", "before") == (
        _m(3, phase="after", order=5), _m(1, phase="before", order=0), _m(2, phase="before", order=1),
        _m(9, "video", "before", 2))
    assert append_media([], 9, "photo", "after") == (_m(9, order=0),)


def test_덧붙여도_알림장에서_뺀_표시는_남고_새_미디어는_보인다():
    """R5 — 순서를 다시 매기는 칸이든 아니든 뺀 것은 뺀 채다."""
    media = [replace(_m(1, phase="before", order=3), hidden=True), _m(2, phase="before", order=90),
             replace(_m(3, phase="after", order=5), hidden=True)]
    assert [(m.media_id, m.sort_order, m.hidden) for m in append_media(media, 9, "photo", "before")] == [
        (3, 5, True), (1, 0, True), (2, 1, False), (9, 2, False)]
