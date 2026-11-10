from datetime import time

import pytest

from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS, NotificationSettings
from notification.domain.value_objects.channel_status import LINKED, TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    DEFAULT_KINDS,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
    SCHEDULED_KINDS,
)
from notification.domain.value_objects.message_status import (
    DELIVERED_STATUSES,
    FALLBACK_SENT,
    PENDING_STATUSES,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.tests.helpers.builders import channel, kst, settings


def test_종류의_순서와_집합():
    assert KINDS == (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT)
    assert DEFAULT_KINDS == (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL)
    assert SCHEDULED_KINDS == frozenset({REMINDER, NEXT_VISIT})
    assert PENDING_STATUSES == frozenset({SCHEDULED, SENDING})
    assert DELIVERED_STATUSES == frozenset({SENT, FALLBACK_SENT})


@pytest.mark.parametrize(("status", "linked"), [(TOKEN_REQUESTED, False), (LINKED, True), (UNLINKED, False)])
def test_연동됨은_상태가_linked_일_때뿐이다(status, linked):
    assert channel(status=status).is_linked is linked


def test_문자_대체는_켜져_있고_발신번호_인증까지_마쳐야_한다():
    assert channel(sms_fallback_enabled=False).can_fallback is False
    assert channel(sms_fallback_enabled=True, sender_number="0212345678",
                   sender_number_verified_at=None).can_fallback is False
    assert channel(sms_fallback_enabled=True, sender_number="0212345678",
                   sender_number_verified_at=kst(10, 3, 10)).can_fallback is True


def test_처음_설정은_다음_예약_제안만_꺼져_있고_18시_30일이다():
    assert DEFAULT_NOTIFICATION_SETTINGS == NotificationSettings(
        confirm_enabled=True, reminder_enabled=True, report_enabled=True, change_enabled=True,
        next_visit_enabled=False, reminder_time=time(18, 0), next_visit_after_weeks=None,
        next_visit_cooldown_days=30,
    )


@pytest.mark.parametrize(("kind", "field"), [
    (CONFIRM, "confirm_enabled"), (REMINDER, "reminder_enabled"), (REPORT, "report_enabled"),
    (CHANGE, "change_enabled"), (CANCEL, "change_enabled"), (NEXT_VISIT, "next_visit_enabled"),
])
def test_종류마다_켜짐을_정하는_칸이_있고_취소는_변경_칸을_따른다(kind, field):
    everything_on = {f: True for f in (
        "confirm_enabled", "reminder_enabled", "report_enabled", "change_enabled", "next_visit_enabled")}
    assert settings(**everything_on).enabled_for(kind) is True
    assert settings(**{**everything_on, field: False}).enabled_for(kind) is False


@pytest.mark.parametrize("fields, under_review, asks", [
    (dict(status="pending", provider_template_id="TP-V1"), True, "TP-V1"),
    (dict(status="approved", provider_template_id="TP-V1"), False, "TP-V1"),
    (dict(status="approved", provider_template_id="TP-V1", pending_text_version=2,
          pending_provider_template_id="TP-V2"), True, "TP-V2"),
    (dict(status="rejected", provider_template_id="TP-V1"), False, "TP-V1"),
])
def test_템플릿은_첫_판이_pending_이거나_대기_판이_있으면_심사_중이고_물을_업체_ID_는_심사_중인_판의_것이다(
    fields, under_review, asks,
):
    from notification.tests.helpers.builders import template

    found = template(**fields)
    assert (found.under_review, found.review_provider_template_id) == (under_review, asks)
