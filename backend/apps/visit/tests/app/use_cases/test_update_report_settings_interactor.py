import pytest

from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.app.use_cases.update_report_settings_interactor import UpdateReportSettingsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeReportSettingsRepository, FakeSchedule, Journal


def _settings(link_days) -> ReportSettings:
    return ReportSettings(link_days=link_days, show_menus=False, show_shop_info=True, show_weight=True,
                          show_amount=False)


def _interactor(journal: Journal):
    settings = FakeReportSettingsRepository(journal)
    return UpdateReportSettingsInteractor(schedule=FakeSchedule(journal), settings=settings), settings


@pytest.mark.parametrize("link_days", [7, 30, None])
async def test_수정은_설정_행을_준비한_뒤_바꾼다(link_days):
    journal = Journal()
    interactor, settings = _interactor(journal)
    changed = await interactor.update_report_settings(
        UpdateReportSettingsCommand(ctx=ctx(), settings=_settings(link_days)))
    assert changed == _settings(link_days) == settings.rows[1]
    assert journal == [("ensure", 1), ("update_report_settings", 1)]


@pytest.mark.parametrize("link_days", [0, 1, 8, 31, -7, 365])
async def test_고를_수_없는_기간이면_쓰지_않는다(link_days):
    journal = Journal()
    interactor, _ = _interactor(journal)
    with pytest.raises(VisitInputError):
        await interactor.update_report_settings(
            UpdateReportSettingsCommand(ctx=ctx(), settings=_settings(link_days)))
    assert journal == []
