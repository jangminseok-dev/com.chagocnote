from __future__ import annotations

from typing import Any

from pydantic import BaseModel, StrictBool, StrictInt

from visit.domain.services.revisit_rules import DEFAULT_REVISIT_MESSAGE
from visit.domain.value_objects.revisit_settings import DEFAULT_REVISIT_SETTINGS, RevisitSettings


class RevisitSettingsValuesSchema(BaseModel):
    default_cycle_weeks: int       # 주기를 모르는 아이의 다음 미용(주, 1~52)
    revisit_soon_days: int         # 다시 올 날 며칠 전부터 '곧'(1~30)
    revisit_message: str | None    # 안내 글 템플릿 — null 이면 처음 글
    count_unsent_reports: bool     # 알림장을 안 보낸 방문을 남은 일로 세기
    cycle_sample_visits: int       # 주기 계산에서 볼 최근 방문 수(3~12)
    cycle_min_gap_days: int        # 이보다 짧은 간격은 손질로 보고 뺀다(0~28)


class RevisitSettingsSchema(RevisitSettingsValuesSchema):
    defaults: RevisitSettingsValuesSchema   # 처음 값 — 앱이 [처음 값으로]·처음 글을 보일 때 쓴다

    @classmethod
    def of(cls, s: RevisitSettings) -> RevisitSettingsSchema:
        d = DEFAULT_REVISIT_SETTINGS
        return cls(
            **_values(s),
            defaults=RevisitSettingsValuesSchema(**{**_values(d), "revisit_message": DEFAULT_REVISIT_MESSAGE}),
        )


def _values(s: RevisitSettings) -> dict[str, Any]:
    return {
        "default_cycle_weeks": s.default_cycle_weeks, "revisit_soon_days": s.revisit_soon_days,
        "revisit_message": s.revisit_message, "count_unsent_reports": s.count_unsent_reports,
        "cycle_sample_visits": s.cycle_sample_visits, "cycle_min_gap_days": s.cycle_min_gap_days,
    }


class UpdateRevisitSettingsRequestSchema(BaseModel):
    """보낸 칸만 바뀐다(빠진 칸은 지금 값). revisit_message 의 null 은 처음 글로 돌아가기다.
    범위·빈 글은 도메인이 본다(422). 길이 상한은 입력 경계다."""

    default_cycle_weeks: StrictInt | None = None
    revisit_soon_days: StrictInt | None = None
    revisit_message: str | None = None
    count_unsent_reports: StrictBool | None = None
    cycle_sample_visits: StrictInt | None = None
    cycle_min_gap_days: StrictInt | None = None

    def changes(self) -> dict[str, Any]:
        sent = {name: getattr(self, name) for name in self.model_fields_set}
        # null 을 받을 수 있는 칸은 메시지뿐이다 — 숫자·켜고 끄기의 null 은 보내지 않은 것으로 친다.
        return {k: v for k, v in sent.items() if v is not None or k == "revisit_message"}
