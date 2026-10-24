"""저장된 variables(구독자가 넣은 ISO 문자열)로 문안 변수와 문안을 만든다. 디스패처(보낼 때)와 API(share_text)가 같이 쓴다."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from notification.domain.services.templates import RenderedMessage, render, variables_for


def _at(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def message_variables(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> dict[str, str]:
    """문안 변수(이름: 값, `#{}` 없음). 업체에 넘기는 사전이자 render 의 입력이다."""
    interval = variables.get("interval_weeks")
    return variables_for(
        kind, shop_name=shop_name, target=target, starts_at=datetime.fromisoformat(variables["starts_at"]), tz=tz,
        previous_starts_at=_at(variables.get("previous_starts_at")), url=variables.get("url"),
        expires_at=_at(variables.get("expires_at")), last_visit_at=_at(variables.get("completed_at")),
        interval_weeks=int(interval) if interval is not None else None,
    )


def message_text(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> RenderedMessage:
    return render(kind, message_variables(kind, shop_name=shop_name, target=target, tz=tz, variables=variables))
