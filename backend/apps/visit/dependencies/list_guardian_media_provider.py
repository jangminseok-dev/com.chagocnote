from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.list_guardian_media_use_case import ListGuardianMediaUseCase
from visit.app.use_cases.list_guardian_media_interactor import ListGuardianMediaInteractor
from visit.dependencies.hub_ports import get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import build_report_repository


def get_list_guardian_media_use_case(
    db: DbSession,
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> ListGuardianMediaUseCase:
    return ListGuardianMediaInteractor(build_report_repository(db), library, shops)
