from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaUrls:
    """사진·영상 하나의 읽기 URL 과 표시용 정보. 목록·달력·피드·미리보기는 thumb, 상세 넘기기는 display
    (영상은 None — 포스터 thumb 를 쓴다), 크게 보기·원본 저장·영상 재생은 original 을 쓴다.

    URL 은 매장 시간대 04:00 기준으로 하루 동안 같고 최대 48시간 유효하다. 앱은 media_id 를 캐시 키로 쓴다.
    """

    media_id: int
    kind: str                     # photo · video
    original_url: str
    display_url: str | None
    thumb_url: str
    width: int
    height: int
    duration_seconds: int | None
