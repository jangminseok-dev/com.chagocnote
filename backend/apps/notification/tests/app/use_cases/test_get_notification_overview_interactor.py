"""한눈에 보기 — 채널·설정·템플릿(종류 순)을 읽기만 한다. 연동 전엔 채널 None·설정 None·템플릿 빈 목록."""
from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.domain.value_objects.message_kind import DEFAULT_KINDS
from notification.tests.helpers.builders import ctx
from notification.tests.helpers.onboarding_world import OnboardingWorld


async def test_연동된_매장은_채널_설정_템플릿을_종류_순으로_본다():
    world = OnboardingWorld()
    view = await world.overview.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx()))
    assert view.channel == world.channels.rows[1] and view.settings == world.settings.rows[1]
    assert [t.kind for t in view.templates] == list(DEFAULT_KINDS)


async def test_연동_전엔_전부_비어_있고_아무것도_쓰지_않는다():
    world = OnboardingWorld(linked=False)
    view = await world.overview.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx()))
    assert (view.channel, view.settings, view.templates) == (None, None, [])
    assert world.journal == []


async def test_다른_매장의_것은_보지_않는다():
    world = OnboardingWorld()
    view = await world.overview.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx(shop_id=2)))
    assert (view.channel, view.settings, view.templates) == (None, None, [])
