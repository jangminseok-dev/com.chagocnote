"""문진표 끝의 동의서(⑪ 설계 3.4 — 문진표 끝에서 동의서까지). 순수 함수 — DB 도 시계도 모른다.

답으로 보아 노령이거나 지병을 골랐으면 동의서 구역이 나타난다. 매장이 `모든 아이에게` 를 켰으면 늘 나타난다.
웹이 같은 규칙으로 구역을 그리고, 제출이 이 규칙으로 다시 본다.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date

from customer.domain.entities.consent import ConsentPolicy
from customer.domain.services.consent_text import PARTS
from customer.domain.services.intake_rules import CleanAnswer
from customer.domain.services.pet_age import age_years


def consent_parts(answer: CleanAnswer, *, on: date, policy: ConsentPolicy, for_all: bool) -> tuple[str, ...]:
    """이 답에 붙는 토막. 빈 튜플이면 동의서가 없다. 나이를 모르거나 칸을 껐으면 노령이 아니다."""
    age = age_years(answer.birth_date, answer.birth_year, on)
    senior = age is not None and age >= policy.senior_age
    condition = answer.no_known_conditions is False and bool(answer.conditions)
    if not (for_all or senior or condition):
        return ()
    return ("basic",) + (("senior",) if senior else ()) + (("condition",) if condition else ())


def shown_conditions(answer: CleanAnswer, labels: Mapping[str, str]) -> tuple[str, ...]:
    """동의서에 보이는 지병 이름 — 직접 적은 이름이 있으면 그것, 없으면 종류의 이름. 메모는 보이지 않는다."""
    return tuple(c.custom_label or labels.get(c.type_code, c.type_code) for c in answer.conditions)


def texts_digest(versions: Mapping[str, tuple[str, int]], policy: ConsentPolicy, for_all: bool) -> str:
    """보호자가 연 문진표의 동의서 구역이 무엇으로 조립됐는지의 지문. versions 는 토막 → (글의 출처, 판).

    낼 때 다시 계산해 다르면 받지 않는다 — 연 뒤 매장이 글을 고쳤거나 노령 나이·`모든 아이에게` 를 바꿨다.
    """
    material = [policy.senior_age, for_all, [[part, *versions[part]] for part in PARTS]]
    raw = json.dumps(material, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
