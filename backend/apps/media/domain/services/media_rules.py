"""무엇을 받는가 — 종류·형식·크기·길이, 그리고 객체 키 규칙(설계 7.2).

서버는 파일을 디코딩하지 않는다. 가로·세로·길이는 앱이 선언한 값을 표시용으로 믿고 범위만 본다.
"""
from __future__ import annotations

from dataclasses import dataclass

from media.domain.errors import MediaInputError, MediaTooLargeError, MediaTypeUnsupportedError

PHOTO = "photo"
VIDEO = "video"
KINDS = (PHOTO, VIDEO)

CONTENT_TYPE = {PHOTO: "image/jpeg", VIDEO: "video/mp4"}
MAX_BYTES = {PHOTO: 20 * 1024 * 1024, VIDEO: 200 * 1024 * 1024}
MAX_VIDEO_SECONDS = 60
MAX_SIDE = 10_000   # 긴 변 3000px 로 줄여 올리지만, 선언값이 말이 되는지만 본다


@dataclass(frozen=True)
class MediaKeys:
    """객체 하나가 저장소에 남기는 키. 사진은 원본·표시용·썸네일 셋, 영상은 원본·포스터(썸네일) 둘."""

    original: str
    display: str | None
    thumb: str

    def all(self) -> tuple[str, ...]:
        return tuple(k for k in (self.original, self.display, self.thumb) if k is not None)


def object_keys(shop_id: int, media_id: int, kind: str) -> MediaKeys:
    """렌디션이 키의 **앞**에 온다 — S3 수명주기 규칙은 접두사로만 거를 수 있어서, 원본만 싼 저장 계층으로
    옮기려면(설계 7.4) 원본이 한 접두사 아래 모여야 한다. 영상 원본은 더 늦게 더 싼 계층으로 가므로 따로 둔다."""
    tail = f"shops/{shop_id}/{media_id}"
    if kind == PHOTO:
        return MediaKeys(original=f"original/{tail}.jpg", display=f"display/{tail}.jpg", thumb=f"thumb/{tail}.jpg")
    return MediaKeys(original=f"original-video/{tail}.mp4", display=None, thumb=f"thumb/{tail}.jpg")


def check_upload(
    kind: str, content_type: str, byte_size: int, width: int, height: int, duration_seconds: int | None
) -> None:
    """발급 전에 선언값을 본다. 크기는 확인(HEAD) 때 실제 값으로 한 번 더 본다."""
    if kind not in KINDS or CONTENT_TYPE[kind] != content_type:
        raise MediaTypeUnsupportedError("사진은 image/jpeg, 영상은 video/mp4 만 올릴 수 있습니다.")
    check_size(kind, byte_size)
    if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE):
        raise MediaInputError("가로·세로가 올바르지 않습니다.")
    if kind == VIDEO and (duration_seconds is None or not 1 <= duration_seconds <= MAX_VIDEO_SECONDS):
        raise MediaInputError("영상은 1초에서 60초까지 올릴 수 있습니다.")
    if kind == PHOTO and duration_seconds is not None:
        raise MediaInputError("사진에는 길이가 없습니다.")


def check_size(kind: str, byte_size: int) -> None:
    if not 1 <= byte_size <= MAX_BYTES[kind]:
        raise MediaTooLargeError("사진은 20MB, 영상은 200MB 까지 올릴 수 있습니다.")
