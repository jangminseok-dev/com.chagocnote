from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsentLink:
    """보낼 것 묶음에 실을 동의서 링크. 주소를 로그에 남기지 않는다."""

    url: str
    form_id: int
    created: bool         # 이번에 새로 만들었나 — 살아 있던 요청이면 False


@dataclass(frozen=True)
class BundleTexts:
    """보호자에게 보내는 글의 템플릿(⑪ 설계 3.5) — 매장이 고쳤으면 그 글, 아니면 기본 글. 자리(`{날짜}` 등)가 든 채다."""

    reservation: str      # 예약 접수 안내
    consent: str          # 동의서 링크를 보내는 글 — `{링크}` 가 꼭 있다
