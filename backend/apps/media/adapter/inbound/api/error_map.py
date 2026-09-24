"""media 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from media.domain.errors import (
    MediaInputError,
    MediaNotFoundError,
    MediaNotUploadedError,
    MediaTooLargeError,
    MediaTypeUnsupportedError,
)

MEDIA_ERROR_STATUS: dict[type[Exception], int] = {
    MediaNotFoundError: 404,
    MediaNotUploadedError: 409,
    MediaTooLargeError: 422,
    MediaTypeUnsupportedError: 422,
    MediaInputError: 422,
}
