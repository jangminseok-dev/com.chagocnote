"""알림장의 규칙 — 링크 기간, 뺄 사진, 보호자에게 보이는 미디어와 대표, 보낼 수 있는가(설계 4·6절).

판단은 잠근 뒤 다시 읽은 방문과 기록으로 한다.
"""
from __future__ import annotations

import unicodedata
from dataclasses import replace
from urllib.parse import urlsplit
from datetime import datetime, timedelta

from visit.domain.entities.visit import COMPLETED, Visit
from visit.domain.entities.visit_record import AFTER, BEFORE, RecordMedia, VisitRecord
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
)
from visit.domain.services.visit_record_rules import cover_media_id
from visit.domain.value_objects.report_settings import LINK_DAYS, ReportSettings

MAX_HIDDEN = 33   # 방문당 사진 30 + 영상 3


def expires_at_for(now: datetime, link_days: int | None) -> datetime | None:
    return now + timedelta(days=link_days) if link_days is not None else None


def check_settings(settings: ReportSettings) -> None:
    if settings.link_days is not None and settings.link_days not in LINK_DAYS:
        raise VisitInputError("링크 기간은 7일, 30일, 계속 가운데 하나여야 합니다.")
    check_review(settings.review_url, settings.review_text)


# --- 알림장 끝의 리뷰 남기기 줄(⑫ 설계 3.6) ---

DEFAULT_REVIEW_TEXT = "미용이 마음에 드셨다면 후기를 남겨 주세요"
REVIEW_URL_MAX = 300
REVIEW_TEXT_MAX = 60
# 제어 문자·형식 문자(너비 없는 공백·방향 뒤집기 등)·줄·문단 나눔 — 눈에 보이지 않거나 글을 뒤집는 문자.
_HIDDEN = frozenset({"Cc", "Cf", "Zl", "Zp"})


def _has_hidden(text: str) -> bool:
    return any(unicodedata.category(ch) in _HIDDEN for ch in text)


def check_review(url: str | None, text: str | None) -> None:
    """주소는 https 이고 호스트가 있고 계정 정보·공백·제어 문자가 없고 300자까지. 도메인 목록으로 묶지 않는다.
    문구는 60자까지, 줄바꿈·제어 문자가 없고 주소처럼 보이는 글을 담지 않는다(다른 주소를 심지 못하게).
    오류 글에 받은 값을 싣지 않는다."""
    if url is not None:
        bad = VisitInputError("리뷰 주소는 https:// 로 시작하는 300자 이하의 주소여야 합니다.")
        try:
            parts = urlsplit(url)
            host, _ = parts.hostname, parts.port      # 대괄호가 짝이 안 맞는 호스트·숫자가 아닌 포트는 ValueError
        except ValueError:
            raise bad from None                       # 받은 값은 싣지 않는다
        if (len(url) > REVIEW_URL_MAX or parts.scheme != "https" or not host or "@" in parts.netloc
                or any(ch.isspace() for ch in url) or _has_hidden(url)):
            raise bad
    if text is not None:
        lowered = text.lower()
        if len(text) > REVIEW_TEXT_MAX or _has_hidden(text) or "http" in lowered or "www." in lowered:
            raise VisitInputError("리뷰 문구는 60자 이하의 한 줄 글이어야 하고 주소를 담을 수 없습니다.")


def normalized_review_url(url: str | None) -> str | None:
    """스킴만 소문자로(`HTTPS://` → `https://`) — 웹이 다시 볼 때 어긋나지 않게. 나머지는 매장이 넣은 그대로."""
    if url is None or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    return f"{scheme.lower()}://{rest}"


def review_of(settings: ReportSettings, show_review: bool) -> tuple[str | None, str | None]:
    """그 알림장의 리뷰 줄(주소, 문구). 주소가 없거나 그 알림장이 뺐으면 둘 다 없다. 문구가 비면 기본 문구."""
    if settings.review_url is None or not show_review:
        return None, None
    text = settings.review_text.strip() if settings.review_text else ""
    return settings.review_url, text or DEFAULT_REVIEW_TEXT


def check_hidden_ids(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None:
    if len(hidden_ids) > MAX_HIDDEN or len(set(hidden_ids)) != len(hidden_ids):
        raise VisitInputError("뺄 사진·영상은 겹치지 않게 33개까지 고를 수 있습니다.")
    if not set(hidden_ids) <= {m.media_id for m in record.media}:
        raise VisitInputError("이 기록의 사진·영상만 뺄 수 있습니다.")


def hide(record: VisitRecord, hidden_ids: tuple[int, ...]) -> tuple[RecordMedia, ...]:
    """기록의 미디어 전부에 뺀 표시를 다시 매긴다 — 고른 것만 빠지고 나머지는 되살아난다."""
    return tuple(replace(m, hidden=m.media_id in hidden_ids) for m in record.media)


def carry_hidden(previous: tuple[RecordMedia, ...], media: tuple[RecordMedia, ...]) -> tuple[RecordMedia, ...]:
    """기록을 다시 저장할 때 앞선 뺀 표시를 미디어 ID 로 옮긴다. 새로 붙은 미디어는 보인다."""
    hidden = {m.media_id for m in previous if m.hidden}
    return tuple(replace(m, hidden=m.media_id in hidden) for m in media)


def visible_media(record: VisitRecord) -> tuple[RecordMedia, ...]:
    """보호자에게 보이는 미디어 — 빼지 않은 것. 후 → 전, 그 안에서 sort_order."""
    shown = (m for m in record.media if not m.hidden)
    return tuple(sorted(shown, key=lambda m: ({AFTER: 0, BEFORE: 1}[m.phase], m.sort_order)))


def report_cover_media_id(record: VisitRecord) -> int | None:
    return cover_media_id(visible_media(record))


def check_sendable(visit: Visit, record: VisitRecord | None, hidden_ids: tuple[int, ...]) -> None:
    if visit.status != COMPLETED:
        raise VisitNotCompletedError("완료한 방문에서만 알림장을 보낼 수 있습니다.")
    if record is None:
        raise VisitNoRecordYetError("기록을 먼저 남겨 주세요.")
    check_hidden_ids(record, hidden_ids)


def check_not_empty(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None:
    """링크를 새로 만들 때만 본다 — 보낸 뒤 사진을 전부 빼거나 메모를 비우는 것은 막지 않는다."""
    has_media = any(m.media_id not in hidden_ids for m in record.media)
    has_note = bool(record.care_note and record.care_note.strip())
    if not has_media and not has_note:
        raise ReportEmptyError("보낼 사진·영상이나 케어 메모가 없습니다.")
