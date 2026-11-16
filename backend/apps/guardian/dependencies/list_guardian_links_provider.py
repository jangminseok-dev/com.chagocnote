from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from guardian.app.ports.input.list_guardian_links_use_case import ListGuardianLinksUseCase
from guardian.app.use_cases.list_guardian_links_interactor import ListGuardianLinksInteractor
from guardian.dependencies.guardian_wiring import build_link_repository, build_settings_repository
from guardian.dependencies.hub_ports import get_shop_profile
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_list_guardian_links_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile),
) -> ListGuardianLinksUseCase:
    return ListGuardianLinksInteractor(build_link_repository(db), shops, build_settings_repository(db))
