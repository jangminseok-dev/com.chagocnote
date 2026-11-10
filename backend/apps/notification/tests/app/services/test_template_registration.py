"""업체가 준 심사 상태를 적는다 — 첫 판은 status 로, 승인된 줄에 걸린 새 판은 대기 칸으로(설계 2026-11-10 3.2)."""
from notification.app.ports.output.message_gateway_port import TemplateState
from notification.app.services.template_registration import record_template_state
from notification.domain.value_objects.message_kind import CONFIRM
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED
from notification.tests.helpers.builders import ctx, kst, template
from notification.tests.helpers.fakes import FakeTemplates

NOW = kst(10, 20, 9)
A = ctx()
FIRST = dict(status=PENDING, decided_at=None, provider_template_id="TP-V1")
WAITING = dict(status=APPROVED, provider_template_id="TP-V1", pending_text_version=2,
               pending_provider_template_id="TP-V2")


async def _record(fields, state):
    templates = FakeTemplates()
    templates.rows[(1, CONFIRM)] = template(**fields)
    result = await record_template_state(templates, A, templates.rows[(1, CONFIRM)], state, NOW)
    return result, templates.rows[(1, CONFIRM)], templates.journal


async def test_첫_판이_승인되면_approved_로_적는다():
    result, after, _ = await _record(FIRST, TemplateState(status=APPROVED, rejected_reason=None))
    assert (result, after.status, after.decided_at) == ("approved", APPROVED, NOW)


async def test_첫_판이_반려되면_rejected_와_사유를_적는다():
    result, after, _ = await _record(FIRST, TemplateState(status=REJECTED, rejected_reason="사유"))
    assert (result, after.status, after.rejected_reason) == ("rejected", REJECTED, "사유")


async def test_대기_판이_승인되면_본_칸으로_올린다():
    result, after, _ = await _record(WAITING, TemplateState(status=APPROVED, rejected_reason=None))
    assert result == "approved"
    assert (after.status, after.text_version, after.provider_template_id, after.pending_provider_template_id,
            after.decided_at) == (APPROVED, 2, "TP-V2", None, NOW)


async def test_대기_판이_반려되면_옛_판을_두고_rejected_new_version_을_돌려준다():
    result, after, _ = await _record(WAITING, TemplateState(status=REJECTED, rejected_reason="사유"))
    assert result == "rejected_new_version"
    assert (after.status, after.text_version, after.provider_template_id, after.pending_provider_template_id,
            after.rejected_reason) == (APPROVED, 1, "TP-V1", None, "사유")


async def test_아직_심사_중이면_None_이고_저장소를_부르지_않는다():
    for fields in (FIRST, WAITING):
        result, after, journal = await _record(fields, TemplateState(status=PENDING, rejected_reason=None))
        assert result is None and after == template(**fields) and journal == []
