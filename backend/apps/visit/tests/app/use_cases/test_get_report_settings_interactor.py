from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.app.use_cases.get_report_settings_interactor import GetReportSettingsInteractor
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeReportSettingsRepository

WEEK = ReportSettings(link_days=7, show_menus=False, show_shop_info=True, show_weight=True, show_amount=False)


async def test_정한_적이_없는_매장은_기본값을_본다():
    settings = FakeReportSettingsRepository()
    found = await GetReportSettingsInteractor(settings).get_report_settings(GetReportSettingsQuery(ctx=ctx()))
    assert found == DEFAULT_REPORT_SETTINGS
    assert settings.journal == []   # 조회는 아무것도 쓰지 않는다


async def test_조회는_그_매장이_정한_설정을_준다():
    settings = FakeReportSettingsRepository()
    settings.rows[2] = WEEK
    interactor = GetReportSettingsInteractor(settings)
    assert await interactor.get_report_settings(GetReportSettingsQuery(ctx=ctx(shop_id=2))) == WEEK
    assert await interactor.get_report_settings(GetReportSettingsQuery(ctx=ctx(shop_id=1))) == DEFAULT_REPORT_SETTINGS
