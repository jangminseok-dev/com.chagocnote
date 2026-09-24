"""미용 기록의 규칙 — 누가 언제 쓰는가, 입력의 모양, 한도, 버전, 대표 사진(설계 6.2·8절).

기록은 미용 중·완료 방문에만 쓴다. 판단은 잠근 뒤 다시 읽은 방문으로 한다. 상태 클래스에 행동을 더하지 않는다.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_record import AFTER, BEFORE, RecordMedia, VisitRecord
from visit.domain.errors import (
    RecordItemDuplicateError,
    RecordMediaLimitError,
    RecordVersionConflictError,
    RecordWeightWithoutPetError,
    VisitNoRecordYetError,
)
from visit.domain.state.visit_status import STARTED_STATUSES
from visit.domain.value_objects.record_input import RecordInput

MEDIA_LIMITS = {"photo": 30, "video": 3}   # 방문 하나에
MAX_SORT_ORDER = 99


def check_recordable(visit: Visit) -> None:
    if visit.status not in STARTED_STATUSES:
        raise VisitNoRecordYetError("미용을 시작한 방문에만 기록을 쓸 수 있습니다.")


def check_input(visit: Visit, record: RecordInput) -> None:
    if record.weight_kg is not None and visit.pet_id is None:
        raise RecordWeightWithoutPetError("보호자만의 방문에는 몸무게를 적을 수 없습니다.")
    menu_ids = [item.menu_id for item in record.items]
    if len(menu_ids) != len(set(menu_ids)):
        raise RecordItemDuplicateError("같은 메뉴를 두 번 적을 수 없습니다.")


def check_media_limits(kinds: Iterable[str]) -> None:
    counts = Counter(kinds)
    if any(counts[kind] > limit for kind, limit in MEDIA_LIMITS.items()):
        raise RecordMediaLimitError("방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있습니다.")


def check_version(current: VisitRecord | None, requested: int | None) -> None:
    """기록이 없으면 버전을 보내지 않고, 있으면 지금 버전을 보내야 한다. 다르면 그 사이 누가 바꾼 것이다."""
    expected = current.version if current is not None else None
    if requested != expected:
        raise RecordVersionConflictError("다른 기기가 먼저 기록을 바꿨습니다. 다시 불러와 주세요.")


def next_version(current: VisitRecord | None) -> int:
    return current.version + 1 if current is not None else 1


def cover_media_id(media: Iterable[RecordMedia]) -> int | None:
    """대표 사진 — 후 사진 첫 장 → 전 사진 첫 장 → 영상 포스터(후 먼저) → 없음(설계 6.2)."""
    ranked = sorted(
        media,
        key=lambda m: (m.kind != "photo", {AFTER: 0, BEFORE: 1}[m.phase], m.sort_order),
    )
    return ranked[0].media_id if ranked else None
