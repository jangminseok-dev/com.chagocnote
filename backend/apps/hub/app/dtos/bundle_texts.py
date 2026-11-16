from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BundleTexts:
    """보호자에게 보내는 글의 템플릿(⑪ 설계 3.5) — 매장이 고쳤으면 그 글, 아니면 기본 글. 자리(`{날짜}` 등)가 든 채다."""

    reservation: str      # 예약 접수 안내
    consent: str          # 동의서 링크를 보내는 글 — `{링크}` 가 꼭 있다
