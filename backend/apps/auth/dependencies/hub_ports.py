"""허브 포트 자리 — auth 가 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.membership_directory_port import MembershipDirectoryPort
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort


def get_membership_directory() -> MembershipDirectoryPort:
    raise RuntimeError("MembershipDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_membership_lifecycle() -> MembershipLifecyclePort:
    raise RuntimeError("MembershipLifecyclePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
