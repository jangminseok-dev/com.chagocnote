from __future__ import annotations

"""가족과 함께 보기(⑫)의 프로바이더들."""
from fastapi import Depends

from core.database import DbSession
from guardian.app.ports.input.create_family_invite_use_case import CreateFamilyInviteUseCase
from guardian.app.ports.input.end_all_family_use_case import EndAllFamilyUseCase
from guardian.app.ports.input.end_family_member_use_case import EndFamilyMemberUseCase
from guardian.app.ports.input.get_guardian_settings_use_case import GetGuardianSettingsUseCase
from guardian.app.ports.input.join_family_use_case import JoinFamilyUseCase
from guardian.app.ports.input.list_family_use_case import ListFamilyUseCase
from guardian.app.ports.input.update_guardian_settings_use_case import UpdateGuardianSettingsUseCase
from guardian.app.use_cases.create_family_invite_interactor import CreateFamilyInviteInteractor
from guardian.app.use_cases.end_all_family_interactor import EndAllFamilyInteractor
from guardian.app.use_cases.end_family_member_interactor import EndFamilyMemberInteractor
from guardian.app.use_cases.get_guardian_settings_interactor import GetGuardianSettingsInteractor
from guardian.app.use_cases.join_family_interactor import JoinFamilyInteractor
from guardian.app.use_cases.list_family_interactor import ListFamilyInteractor
from guardian.app.use_cases.update_guardian_settings_interactor import UpdateGuardianSettingsInteractor
from guardian.dependencies.guardian_wiring import (
    build_family_limiter, build_invite_repository, build_link_repository, build_settings_repository, utc_now,
)
from guardian.dependencies.hub_ports import get_active_user_guard, get_shop_profile
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_create_family_invite_use_case(
    db: DbSession, users: ActiveUserGuardPort = Depends(get_active_user_guard),
) -> CreateFamilyInviteUseCase:
    return CreateFamilyInviteInteractor(
        build_link_repository(db), build_invite_repository(db), build_settings_repository(db), users,
        build_family_limiter(), now=utc_now)


def get_join_family_use_case(
    db: DbSession, users: ActiveUserGuardPort = Depends(get_active_user_guard),
) -> JoinFamilyUseCase:
    return JoinFamilyInteractor(
        build_link_repository(db), build_invite_repository(db), build_settings_repository(db), users,
        build_family_limiter(), now=utc_now)


def get_list_family_use_case(db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile)) -> ListFamilyUseCase:
    return ListFamilyInteractor(build_link_repository(db), shops, now=utc_now)


def get_end_family_member_use_case(db: DbSession) -> EndFamilyMemberUseCase:
    return EndFamilyMemberInteractor(build_link_repository(db), now=utc_now)


def get_end_all_family_use_case(db: DbSession) -> EndAllFamilyUseCase:
    return EndAllFamilyInteractor(build_link_repository(db), build_invite_repository(db), now=utc_now)


def get_get_guardian_settings_use_case(db: DbSession) -> GetGuardianSettingsUseCase:
    return GetGuardianSettingsInteractor(build_settings_repository(db))


def get_update_guardian_settings_use_case(db: DbSession) -> UpdateGuardianSettingsUseCase:
    return UpdateGuardianSettingsInteractor(build_settings_repository(db))
