from __future__ import annotations

from auth.app.services.provider_revoker import ProviderRevoker
from auth.dependencies.auth_wiring import build_provider_revoker


def get_provider_revoker() -> ProviderRevoker:
    return build_provider_revoker()
