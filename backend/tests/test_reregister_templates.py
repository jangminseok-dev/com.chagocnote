"""템플릿 재등록 스크립트 — 판이 다르거나 반려된 종류만 새 판으로, --refresh 는 pending 의 상태만."""
from notification.app.ports.output.message_gateway_port import GatewayTransientError, TemplateState
from notification.domain.value_objects.channel_status import LINKED, UNLINKED
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED
from notification.tests.helpers.builders import channel, kst, settings, template
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates, Journal, SpyGateway
from scripts.reregister_templates import run

NOW = kst(10, 20, 9)


class _World:
    def __init__(self, **gateway_kwargs) -> None:
        self.journal = Journal()
        self.channels = FakeChannels(self.journal)
        self.settings = FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, templates=self.templates, channels=self.channels)
        self.gateway = SpyGateway(self.journal, **gateway_kwargs)

    def shop(self, shop_id: int, *, linked=True, next_visit=False, templates=()) -> None:
        self.channels.rows[shop_id] = channel(shop_id=shop_id, provider_channel_id=f"pf-{shop_id}",
                                              status=LINKED if linked else UNLINKED)
        self.settings.rows[shop_id] = settings(next_visit_enabled=next_visit)
        for t in templates:
            self.templates.rows[(shop_id, t.kind)] = t

    async def commit(self) -> None:
        self.journal.append(("commit",))

    async def run(self, *, shop_id=None, refresh=False):
        return await run(queue=self.messages, settings=self.settings, templates=self.templates, gateway=self.gateway,
                         commit=self.commit, now=NOW, shop_id=shop_id, refresh=refresh)

    def rows(self, shop_id: int) -> dict[str, tuple[int, str]]:
        return {t.kind: (t.text_version, t.status) for (s, _), t in self.templates.rows.items() if s == shop_id}


def _mixed_world() -> _World:
    world = _World()
    world.shop(1, templates=[
        template(id=1, kind=CONFIRM),                                                   # 판 같고 승인 — 그대로
        template(id=2, kind=REMINDER, text_version=0),                                  # 옛 판 — 새로
        template(id=3, kind=REPORT, status=REJECTED, rejected_reason="변수가 많아요"),   # 반려 — 새로
        template(id=4, kind=CHANGE, status=PENDING, decided_at=None),                   # 심사 중 — 그대로
    ])                                                                                   # cancel 없음 — 새로
    world.shop(2, next_visit=True, templates=[template(id=10 + i, shop_id=2, kind=k) for i, k in enumerate(
        (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL))])                                  # next_visit 만 없음
    world.shop(3, linked=False, templates=[template(id=20, shop_id=3, kind=CONFIRM, status=REJECTED)])
    return world


async def test_판이_다르거나_반려됐거나_없는_종류만_새_판으로_등록하고_next_visit_은_켠_매장만():
    world = _mixed_world()

    results = await world.run()

    assert results == [(1, REMINDER, "registered"), (1, REPORT, "registered"), (1, CANCEL, "registered"),
                       (2, NEXT_VISIT, "registered")]
    # 승인된 옛 판(reminder)은 덮지 않는다 — 심사가 끝날 때까지 옛 판으로 보내고 새 판은 대기 칸에 든다.
    assert world.rows(1) == {CONFIRM: (1, APPROVED), REMINDER: (0, APPROVED), REPORT: (1, PENDING),
                             CHANGE: (1, PENDING), CANCEL: (1, PENDING)}
    waiting = world.templates.rows[(1, REMINDER)]
    assert (waiting.pending_text_version, waiting.pending_provider_template_id) == (1, "tpl-pf-1-reminder-v1")
    assert world.rows(2)[NEXT_VISIT] == (1, PENDING)
    assert world.rows(3) == {CONFIRM: (1, REJECTED)}      # 해제한 매장은 건드리지 않는다
    assert world.templates.rows[(1, REPORT)].rejected_reason is None


async def test_종류마다_업체를_먼저_부르고_저장한_뒤_커밋한다():
    world = _mixed_world()

    await world.run(shop_id=1)

    assert [e for e in world.journal if e[0] != "ensure_settings"] == [
        ("register_template", "pf-1", REMINDER), ("upsert_template", 1, REMINDER), ("commit",),
        ("register_template", "pf-1", REPORT), ("upsert_template", 1, REPORT), ("commit",),
        ("register_template", "pf-1", CANCEL), ("upsert_template", 1, CANCEL), ("commit",),
    ]


async def test_shop_을_주면_그_매장만_본다():
    world = _mixed_world()

    assert await world.run(shop_id=2) == [(2, NEXT_VISIT, "registered")]
    assert world.rows(1)[REMINDER] == (0, APPROVED)


async def test_업체_오류는_그_종류만_건너뛰고_저장하지_않는다():
    world = _mixed_world()
    world.gateway.register_error = GatewayTransientError("3040")

    results = await world.run(shop_id=1)

    assert results == [(1, REMINDER, "failed(3040)"), (1, REPORT, "failed(3040)"), (1, CANCEL, "failed(3040)")]
    assert world.rows(1)[REMINDER] == (0, APPROVED)
    assert not [e for e in world.journal if e[0] in ("upsert_template", "commit")]


async def test_refresh_는_등록하지_않고_pending_의_업체_상태만_적는다():
    world = _World(reject_next_visit=True)
    world.shop(1, next_visit=True, templates=[
        template(id=1, kind=CONFIRM, status=PENDING, decided_at=None, provider_template_id="tpl-pf-1-confirm-v1"),
        template(id=2, kind=NEXT_VISIT, status=PENDING, decided_at=None,
                 provider_template_id="tpl-pf-1-next_visit-v1"),
        template(id=3, kind=REMINDER, text_version=0),                   # 옛 판 — refresh 는 손대지 않는다
        template(id=4, kind=REPORT, status=REJECTED, rejected_reason="반려"),
    ])
    world.shop(2, templates=[template(id=5, shop_id=2, kind=CONFIRM, status=PENDING, decided_at=None)])

    results = await world.run(shop_id=1, refresh=True)

    assert results == [(1, CONFIRM, APPROVED), (1, NEXT_VISIT, REJECTED)]
    assert world.rows(1) == {CONFIRM: (1, APPROVED), NEXT_VISIT: (1, REJECTED), REMINDER: (0, APPROVED),
                             REPORT: (1, REJECTED)}
    assert world.templates.rows[(1, NEXT_VISIT)].rejected_reason == "가짜 반려"
    assert world.templates.rows[(1, CONFIRM)].decided_at == NOW
    assert world.rows(2)[CONFIRM] == (1, PENDING)
    assert not [e for e in world.journal if e[0] in ("register_template", "upsert_template")]
    assert world.journal.count(("commit",)) == 2


# --- 승인된 줄의 새 판(대기 칸) — 설계 2026-11-10 3.2 ---------------------------------------------------------------

def _review(world, shop_id, kind):
    t = world.templates.rows[(shop_id, kind)]
    return (t.status, t.text_version, t.provider_template_id, t.pending_text_version, t.pending_provider_template_id)


def _five(**confirm):
    """다섯 종류가 모두 승인된 매장 — confirm 만 테스트가 바꾼다."""
    return [template(id=1, kind=CONFIRM, **confirm)] + [
        template(id=i, kind=k) for i, k in enumerate((REMINDER, REPORT, CHANGE, CANCEL), start=2)]


async def test_승인된_종류를_새_판으로_재등록하면_대기_칸에_적히고_status_는_approved_다():
    world = _World()
    world.shop(1, templates=_five(text_version=0, provider_template_id="TP-V0"))

    assert await world.run() == [(1, CONFIRM, "registered")]
    assert _review(world, 1, CONFIRM) == (APPROVED, 0, "TP-V0", 1, "tpl-pf-1-confirm-v1")


async def test_새_판이_이미_심사_중이면_다시_등록하지_않는다():
    world = _World()
    world.shop(1, templates=_five(text_version=0, provider_template_id="TP-V0", pending_text_version=1,
                                  pending_provider_template_id="TP-V1"))

    assert await world.run() == []
    assert not [e for e in world.journal if e[0] == "register_template"]


async def test_새_판이_반려된_뒤에는_다시_고른다():
    world = _World()
    world.shop(1, templates=_five(text_version=0, provider_template_id="TP-V0", rejected_reason="사유"))

    assert await world.run() == [(1, CONFIRM, "registered")]
    assert _review(world, 1, CONFIRM)[3:] == (1, "tpl-pf-1-confirm-v1")


async def test_refresh_는_대기_판도_묻고_승인이면_본_칸으로_올린다():
    world = _World()
    world.shop(1, templates=_five(text_version=0, provider_template_id="TP-V0", pending_text_version=1,
                                  pending_provider_template_id="TP-V1"))

    assert await world.run(refresh=True) == [(1, CONFIRM, "approved")]
    assert ("template_state", "TP-V1") in world.journal
    assert _review(world, 1, CONFIRM) == (APPROVED, 1, "TP-V1", None, None)


async def test_refresh_에서_대기_판이_반려되면_rejected_new_version_이고_옛_판이_남는다():
    world = _World()
    world.shop(1, templates=_five(text_version=0, provider_template_id="TP-V0", pending_text_version=1,
                                  pending_provider_template_id="TP-V1"))
    world.gateway.template_states["TP-V1"] = TemplateState(status=REJECTED, rejected_reason="사유")

    assert await world.run(refresh=True) == [(1, CONFIRM, "rejected_new_version")]
    assert _review(world, 1, CONFIRM) == (APPROVED, 0, "TP-V0", None, None)


async def test_refresh_에서_아직_심사_중이면_pending_이다():
    world = _World()
    world.shop(1, templates=_five(text_version=0, provider_template_id="TP-V0", pending_text_version=1,
                                  pending_provider_template_id="TP-V1"))
    world.gateway.template_states["TP-V1"] = TemplateState(status=PENDING, rejected_reason=None)

    assert await world.run(refresh=True) == [(1, CONFIRM, "pending")]
    assert world.journal.count(("commit",)) == 0
