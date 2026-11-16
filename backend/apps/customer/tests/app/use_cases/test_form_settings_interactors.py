"""서류 설정 읽기·바꾸기(⑪-B) — 규칙을 지나야 저장된다."""
from dataclasses import replace

import pytest

from customer.app.dtos.get_form_settings_dto import GetFormSettingsQuery
from customer.app.dtos.update_form_settings_dto import UpdateFormSettingsCommand
from customer.app.use_cases.get_form_settings_interactor import GetFormSettingsInteractor
from customer.app.use_cases.update_form_settings_interactor import UpdateFormSettingsInteractor
from customer.domain.errors import CustomerInputError
from customer.domain.value_objects.form_settings import DEFAULT_FORM_SETTINGS
from customer.tests.app.use_cases.test_consent_interactors import ctx


class _Settings:
    def __init__(self):
        self.saved = None

    async def get(self, ctx):
        return self.saved or DEFAULT_FORM_SETTINGS

    async def put(self, ctx, settings):
        self.saved = settings
        return settings


async def test_정한_적이_없으면_기본값을_읽는다():
    assert await GetFormSettingsInteractor(_Settings()).get_form_settings(
        GetFormSettingsQuery(ctx=ctx())) == DEFAULT_FORM_SETTINGS


async def test_규칙에_맞으면_저장하고_어긋나면_저장하지_않는다():
    store = _Settings()
    changed = replace(DEFAULT_FORM_SETTINGS, senior_age=8)

    assert await UpdateFormSettingsInteractor(store).update_form_settings(
        UpdateFormSettingsCommand(ctx=ctx(), settings=changed)) == changed
    with pytest.raises(CustomerInputError):
        await UpdateFormSettingsInteractor(store).update_form_settings(
            UpdateFormSettingsCommand(ctx=ctx(), settings=replace(changed, senior_age=3)))
    assert store.saved == changed
