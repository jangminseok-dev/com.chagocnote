"""구조 계약(.importlinter)이 apps/ 의 모든 스포크를 나열하는지 — 빠진 스포크는 계약이 보지 않은 채 통과한다."""
import configparser
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
_SPOKES = sorted(
    p.name for p in (_BACKEND / "apps").iterdir() if (p / "__init__.py").exists() and p.name != "hub"
)
_CONTRACT = "importlinter:contract:"


def _listed(section: str, key: str) -> set[str]:
    config = configparser.ConfigParser()
    config.read(_BACKEND / ".importlinter", encoding="utf-8")
    return set(config[section][key].split())


@pytest.mark.parametrize(("section", "key", "expected"), [
    ("importlinter", "root_packages", {"hub", "core", *_SPOKES}),
    (_CONTRACT + "clean-architecture", "containers", {"hub", *_SPOKES}),
    (_CONTRACT + "spoke-independence", "modules", set(_SPOKES)),
    (_CONTRACT + "framework-isolation", "source_modules",
     {"hub.app", *(f"{s}.app" for s in _SPOKES), *(f"{s}.domain" for s in _SPOKES)}),
    (_CONTRACT + "domain-purity", "source_modules", {f"{s}.domain" for s in _SPOKES}),
    (_CONTRACT + "hub-isolation", "forbidden_modules", set(_SPOKES)),
    (_CONTRACT + "core-isolation", "forbidden_modules", set(_SPOKES)),
])
def test_구조_계약은_모든_스포크를_나열한다(section, key, expected):
    assert _listed(section, key) == expected
