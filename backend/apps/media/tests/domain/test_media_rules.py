import pytest

from media.domain.errors import MediaInputError, MediaTooLargeError, MediaTypeUnsupportedError
from media.domain.services.media_rules import MAX_BYTES, check_upload, object_keys

MB = 1024 * 1024


def test_사진은_원본_표시용_썸네일_세_키를_갖는다():
    keys = object_keys(7, 42, "photo")
    assert keys.all() == ("original/shops/7/42.jpg", "display/shops/7/42.jpg", "thumb/shops/7/42.jpg")


def test_영상은_원본과_포스터_두_키를_갖는다():
    keys = object_keys(7, 43, "video")
    assert (keys.display, keys.all()) == (None, ("original-video/shops/7/43.mp4", "thumb/shops/7/43.jpg"))


def test_받는_선언값():
    check_upload("photo", "image/jpeg", 20 * MB, 3000, 2000, None)
    check_upload("video", "video/mp4", 200 * MB, 1920, 1080, 60)


@pytest.mark.parametrize("kind, content_type", [
    ("photo", "image/heic"), ("photo", "video/mp4"), ("video", "video/quicktime"), ("audio", "audio/mpeg"),
])
def test_종류와_형식이_맞지_않으면_MEDIA_TYPE_UNSUPPORTED(kind, content_type):
    with pytest.raises(MediaTypeUnsupportedError):
        check_upload(kind, content_type, MB, 100, 100, 10 if kind == "video" else None)


@pytest.mark.parametrize("kind, size", [("photo", 20 * MB + 1), ("video", 200 * MB + 1), ("photo", 0)])
def test_한도_밖의_크기는_MEDIA_TOO_LARGE(kind, size):
    content_type = "image/jpeg" if kind == "photo" else "video/mp4"
    with pytest.raises(MediaTooLargeError):
        check_upload(kind, content_type, size, 100, 100, 10 if kind == "video" else None)


def test_한도는_종류마다_다르다():
    assert MAX_BYTES == {"photo": 20 * MB, "video": 200 * MB}


@pytest.mark.parametrize("kind, width, height, duration", [
    ("photo", 0, 100, None), ("photo", 100, 10_001, None), ("photo", 100, 100, 5),
    ("video", 100, 100, None), ("video", 100, 100, 0), ("video", 100, 100, 61),
])
def test_가로세로와_길이의_경계(kind, width, height, duration):
    content_type = "image/jpeg" if kind == "photo" else "video/mp4"
    with pytest.raises(MediaInputError):
        check_upload(kind, content_type, 1000, width, height, duration)
