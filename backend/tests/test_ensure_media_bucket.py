"""미디어 버킷 준비 스크립트 — 원본만 계층을 옮기는 규칙, 여러 번 돌려도 같은 결과."""
import pytest

from scripts.ensure_media_bucket import ensure_bucket, lifecycle_rules, storage_client


def test_원본만_접두사로_골라_옮긴다():
    rules = {r["Filter"]["Prefix"]: [(t["Days"], t["StorageClass"]) for t in r["Transitions"]]
             for r in lifecycle_rules()}
    assert rules == {"original/": [(30, "STANDARD_IA")],
                     "original-video/": [(30, "STANDARD_IA"), (90, "GLACIER_IR")]}


@pytest.mark.integration
def test_두_번_돌려도_된다_MinIO_는_규칙을_건너뛴다():
    client = storage_client()
    first = ensure_bucket(client, "chagocnote-test-ensure")
    second = ensure_bucket(client, "chagocnote-test-ensure")
    assert second[0] == "버킷 chagocnote-test-ensure 이(가) 이미 있습니다."
    assert first[-1] == second[-1] == "이 저장소는 계층 이동을 받지 않아 수명주기 규칙을 건너뜁니다(개발용 MinIO)."
