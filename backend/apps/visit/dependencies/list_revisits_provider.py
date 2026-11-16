from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.list_revisits_use_case import ListRevisitsUseCase
from visit.app.use_cases.list_revisits_interactor import ListRevisitsInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_record_repository,
    build_revisit_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_list_revisits_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> ListRevisitsUseCase:
    return ListRevisitsInteractor(
        history=build_visit_repository(db), directory=directory, records=build_record_repository(db),
        library=library, settings=build_revisit_settings_repository(db), shops=shops, now=utc_now,
    )
