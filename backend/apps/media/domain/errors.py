class MediaError(Exception):
    """media 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "MEDIA_ERROR"


class MediaNotFoundError(MediaError):
    """없거나 다른 매장의 미디어다. 404."""

    code = "MEDIA_NOT_FOUND"


class MediaNotUploadedError(MediaError):
    """발급한 객체가 저장소에 아직 다 올라오지 않았다. 409 — 올린 뒤 다시 확인하면 된다."""

    code = "MEDIA_NOT_UPLOADED"


class MediaTooLargeError(MediaError):
    """종류별 한도(사진 20MB·영상 200MB)를 넘는다. 422."""

    code = "MEDIA_TOO_LARGE"


class MediaTypeUnsupportedError(MediaError):
    """받지 않는 종류·형식이거나 선언과 다른 형식이 올라왔다. 422."""

    code = "MEDIA_TYPE_UNSUPPORTED"


class MediaInputError(MediaError):
    """형식은 맞지만 규칙에 어긋난 값(가로세로·길이). 422."""

    code = "VALIDATION_ERROR"
