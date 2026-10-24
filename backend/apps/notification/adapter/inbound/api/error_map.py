"""notification 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    MessageNotRetryableError,
    NotificationInputError,
    ProviderUnavailableError,
    SenderNotVerifiedError,
    TemplateNotApprovedError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)

NOTIFICATION_ERROR_STATUS: dict[type[Exception], int] = {
    NotificationInputError: 422,
    ChannelNotLinkedError: 409,
    ChannelAlreadyLinkedError: 409,
    TokenInvalidError: 400,
    SenderNotVerifiedError: 409,
    TemplateNotApprovedError: 409,
    MessageAlreadyPendingError: 409,
    MessageNotFoundError: 404,
    MessageNotRetryableError: 409,
    TooManyNotificationRequestsError: 429,
    ProviderUnavailableError: 502,
}
