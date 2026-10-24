from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.ports.input.get_notification_message_use_case import GetNotificationMessageUseCase
from notification.app.use_cases.get_notification_message_interactor import GetNotificationMessageInteractor
from notification.dependencies.hub_ports import get_customer_directory, get_shop_profile
from notification.dependencies.notification_wiring import build_message_repository


def get_get_notification_message_use_case(
    db: DbSession,
    shops: ShopProfilePort = Depends(get_shop_profile),
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> GetNotificationMessageUseCase:
    return GetNotificationMessageInteractor(messages=build_message_repository(db), shops=shops, directory=directory)
