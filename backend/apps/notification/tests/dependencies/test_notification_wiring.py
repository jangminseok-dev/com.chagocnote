"""발송 게이트웨이 조립 — 키가 둘 다 있으면 솔라피, 둘 다 비고 dev 면 가짜, 그 밖은 기동 실패(설계 6.1)."""
from __future__ import annotations

import pytest

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
from notification.dependencies import notification_wiring as wiring


def test_키가_둘_다_있으면_솔라피_어댑터다():
    assert isinstance(wiring.build_message_gateway("key", "secret", "prod"), SolapiGateway)
    assert isinstance(wiring.build_message_gateway("key", "secret", "dev"), SolapiGateway)


def test_키가_둘_다_비고_dev_면_가짜_어댑터다():
    assert isinstance(wiring.build_message_gateway("", "", "dev"), FakeGateway)


def test_운영에서_키가_비면_기동하지_않는다():
    with pytest.raises(RuntimeError, match="SOLAPI_API_KEY"):
        wiring.build_message_gateway("", "", "prod")


@pytest.mark.parametrize("api_key, api_secret", [("key", ""), ("", "secret")])
def test_키가_하나만_있으면_환경과_상관없이_기동하지_않는다(api_key, api_secret):
    with pytest.raises(RuntimeError, match="SOLAPI_API_KEY"):
        wiring.build_message_gateway(api_key, api_secret, "dev")


def test_프로세스에_하나만_만들고_되돌리면_새로_만든다(monkeypatch):
    monkeypatch.setattr(wiring, "SOLAPI_API_KEY", "")
    monkeypatch.setattr(wiring, "SOLAPI_API_SECRET", "")
    monkeypatch.setattr(wiring, "APP_ENV", "dev")
    wiring.reset_message_gateway()
    first = wiring.get_message_gateway()
    assert first is wiring.get_message_gateway()
    wiring.reset_message_gateway()
    assert wiring.get_message_gateway() is not first
    wiring.reset_message_gateway()
