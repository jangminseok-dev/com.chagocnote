from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.get_sales_summary_use_case import GetSalesSummaryUseCase
from visit.app.use_cases.get_sales_summary_interactor import GetSalesSummaryInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_sales_goal_repository,
    build_sales_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_get_sales_summary_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> GetSalesSummaryUseCase:
    return GetSalesSummaryInteractor(
        sales=build_sales_repository(db), goals=build_sales_goal_repository(db), menus=build_menu_repository(db),
        directory=directory, records=build_record_repository(db), library=library, now=utc_now,
    )
