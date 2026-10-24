"""notification 오류의 계약 — 모든 오류가 HTTP 상태를 갖고 code 가 서로 다르다(tests/test_hub_errors.py 방식)."""
import pytest

from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    MessageNotRetryableError,
    NotificationError,
    NotificationInputError,
    ProviderUnavailableError,
    SenderNotVerifiedError,
    TemplateNotApprovedError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)


def _all_errors(base=NotificationError) -> set[type]:
    found = set()
    for sub in base.__subclasses__():
        found.add(sub)
        found |= _all_errors(sub)
    return found


def test_모든_notification_오류가_HTTP_상태를_갖는다():
    missing = sorted(e.__name__ for e in _all_errors() if e not in NOTIFICATION_ERROR_STATUS)
    assert missing == [], f"{missing} 가 error_map.py 의 NOTIFICATION_ERROR_STATUS 에 없다"


def test_맵에는_notification_오류만_있다():
    stray = sorted(e.__name__ for e in NOTIFICATION_ERROR_STATUS if not issubclass(e, NotificationError))
    assert stray == []


def test_오류_코드는_서로_다르다():
    codes = [e.code for e in _all_errors()]
    assert len(codes) == len(set(codes)), "같은 code 를 가진 오류가 둘 이상이다"


@pytest.mark.parametrize(("error", "code", "status"), [
    (NotificationInputError, "VALIDATION_ERROR", 422),
    (ChannelNotLinkedError, "NOTIFICATION_CHANNEL_NOT_LINKED", 409),
    (ChannelAlreadyLinkedError, "NOTIFICATION_CHANNEL_LINKED", 409),
    (TokenInvalidError, "NOTIFICATION_TOKEN_INVALID", 400),
    (SenderNotVerifiedError, "NOTIFICATION_SENDER_NOT_VERIFIED", 409),
    (TemplateNotApprovedError, "NOTIFICATION_TEMPLATE_NOT_APPROVED", 409),
    (MessageAlreadyPendingError, "NOTIFICATION_ALREADY_PENDING", 409),
    (MessageNotFoundError, "NOTIFICATION_MESSAGE_NOT_FOUND", 404),
    (MessageNotRetryableError, "NOTIFICATION_NOT_RETRYABLE", 409),
    (TooManyNotificationRequestsError, "NOTIFICATION_RATE_LIMITED", 429),
    (ProviderUnavailableError, "NOTIFICATION_PROVIDER_UNAVAILABLE", 502),
])
def test_오류의_코드와_상태(error, code, status):
    assert error.code == code
    assert NOTIFICATION_ERROR_STATUS[error] == status
