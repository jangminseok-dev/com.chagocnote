from datetime import timedelta

import pytest

from search.domain.entities.search_document import KINDS, SCOPES, VISIT_KINDS
from search.domain.services.retry import CLAIM_HOLD, retry_delay
from search.domain.services.targets import belongs, target_filter
from search.tests.helpers.builders import doc


def test_방문_대상은_그_방문의_세_글이다():
    for kind in VISIT_KINDS:
        assert belongs(doc(kind, 7), "visit", 7)
        assert not belongs(doc(kind, 8), "visit", 7)
    assert not belongs(doc("pet_memo", 7, pet_id=7), "visit", 7)
    assert not belongs(doc("customer_memo", 7, pet_id=None), "visit", 7)


def test_반려동물_대상은_그_아이의_특이사항과_지병들이다():
    assert belongs(doc("pet_memo", 101), "pet", 101)
    assert belongs(doc("condition_note", 55, pet_id=101), "pet", 101)     # 지병은 원본 ID 가 아니라 아이로 묶인다
    assert not belongs(doc("condition_note", 101, pet_id=102), "pet", 101)
    assert not belongs(doc("pet_memo", 102, pet_id=102), "pet", 101)
    assert not belongs(doc("care_note", 9, pet_id=101), "pet", 101)       # 그 아이의 방문 글은 방문 대상의 것이다


def test_고객_대상은_보호자_메모_하나다():
    assert belongs(doc("customer_memo", 1, pet_id=None), "customer", 1)
    assert not belongs(doc("customer_memo", 2, customer_id=2, pet_id=None), "customer", 1)
    assert not belongs(doc("pet_memo", 1, customer_id=1, pet_id=1), "customer", 1)


def test_모든_종류는_어느_한_대상에만_든다():
    covered = [k for scope in SCOPES for k in (*target_filter(scope).by_source, *target_filter(scope).by_pet)]
    assert sorted(covered) == sorted(KINDS)


def test_모르는_대상은_거절한다():
    with pytest.raises(ValueError):
        target_filter("shop")


def test_재시도_간격은_30초에서_두_배씩_늘고_한_시간에서_멈춘다():
    assert [retry_delay(n).total_seconds() for n in (0, 1, 2, 6, 7, 30)] == [30, 60, 120, 1920, 3600, 3600]
    assert CLAIM_HOLD == timedelta(seconds=60)
