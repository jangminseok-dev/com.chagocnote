from __future__ import annotations

from dataclasses import dataclass

from customer.domain.entities.consent import ConsentPolicy


@dataclass(frozen=True)
class FormSettings:
    """매장의 서류 설정(⑪ 설계 3.6 의 6). 기본값은 업계에서 흔한 값이고 매장이 자기 가게에 맞게 바꾼다."""

    link_days: int                 # 링크를 열 수 있는 날 수(1~30)
    senior_age: int                # 노령으로 보는 나이(5~20살)
    consent_days: int              # 동의를 다시 받는 기간(30~1095일)
    reservation_text: str | None   # 예약 안내의 템플릿. None 이면 기본 글
    consent_text: str | None       # 동의서 링크를 보내는 글의 템플릿. None 이면 기본 글
    intake_keep_days: int = 30     # 확인하지 않은 문진표를 지우는 날 수(7~90)
    intake_hidden: tuple[str, ...] = ()   # 문진표에서 매장이 끈 칸

    @property
    def policy(self) -> ConsentPolicy:
        return ConsentPolicy(senior_age=self.senior_age, consent_days=self.consent_days, link_days=self.link_days)


DEFAULT_FORM_SETTINGS = FormSettings(
    link_days=14, senior_age=10, consent_days=365, reservation_text=None, consent_text=None,
)
