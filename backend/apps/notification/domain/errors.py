class NotificationError(Exception):
    """notification 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "NOTIFICATION_ERROR"


class NotificationInputError(NotificationError):
    """형식은 맞지만 규칙에 어긋난 입력(리마인드 시각 범위 밖, 주·일수 범위 밖). 422 다."""

    code = "VALIDATION_ERROR"


class ChannelNotLinkedError(NotificationError):
    """연동 전에 설정·재발송. 409."""

    code = "NOTIFICATION_CHANNEL_NOT_LINKED"


class ChannelAlreadyLinkedError(NotificationError):
    """이미 연동된 매장에 다시 연동. 409."""

    code = "NOTIFICATION_CHANNEL_LINKED"


class TokenInvalidError(NotificationError):
    """6자리가 틀렸거나 만료됐다. 400."""

    code = "NOTIFICATION_TOKEN_INVALID"


class SenderNotVerifiedError(NotificationError):
    """발신번호 인증 없이 문자 대체를 켠다. 409."""

    code = "NOTIFICATION_SENDER_NOT_VERIFIED"


class TemplateNotApprovedError(NotificationError):
    """미승인 종류를 다시 보내려 한다. 409."""

    code = "NOTIFICATION_TEMPLATE_NOT_APPROVED"


class MessageAlreadyPendingError(NotificationError):
    """같은 방문·종류의 줄이 대기 중인데 다시 보낸다. 409."""

    code = "NOTIFICATION_ALREADY_PENDING"


class MessageNotFoundError(NotificationError):
    """그 메시지가 없거나 다른 매장의 것이다. 404."""

    code = "NOTIFICATION_MESSAGE_NOT_FOUND"


class MessageNotRetryableError(NotificationError):
    """영구 실패가 아닌 줄에 [다시 보내기]. 409."""

    code = "NOTIFICATION_NOT_RETRYABLE"


class TooManyNotificationRequestsError(NotificationError):
    """토큰·인증번호 요청이 너무 잦다. 429."""

    code = "NOTIFICATION_RATE_LIMITED"


class ProviderUnavailableError(NotificationError):
    """온보딩 요청 중 업체 오류·시간 초과. 502."""

    code = "NOTIFICATION_PROVIDER_UNAVAILABLE"
