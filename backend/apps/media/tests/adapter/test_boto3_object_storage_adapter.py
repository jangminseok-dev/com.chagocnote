"""실제 MinIO(compose)에 올리고 확인하고 지운다. 컨테이너 안에서 PUT 하려고 공개 주소도 내부 주소로 둔다.

버킷은 테스트 사이에 비우지 않으므로 키마다 새 이름을 쓴다.
"""
import uuid
from datetime import datetime, timezone

import httpx
import pytest

from core.config import S3_ACCESS_KEY, S3_ENDPOINT_URL, S3_REGION, S3_SECRET_KEY
from media.adapter.outbound.s3.boto3_object_storage_adapter import Boto3ObjectStorageAdapter
from media.domain.services.url_expiry import signing_window
from media.domain.value_objects.object_info import ObjectInfo
from scripts.ensure_media_bucket import ensure_bucket

pytestmark = pytest.mark.integration

BUCKET = "chagocnote-test"


@pytest.fixture
def storage():
    adapter = Boto3ObjectStorageAdapter(S3_ENDPOINT_URL, S3_ENDPOINT_URL, BUCKET, S3_REGION, S3_ACCESS_KEY,
                                        S3_SECRET_KEY)
    ensure_bucket(adapter._internal, BUCKET)
    return adapter


def _key() -> str:
    return f"thumb/shops/1/{uuid.uuid4().hex}.jpg"


async def test_서명한_URL_로_올리고_HEAD_로_확인하고_읽는다(storage):
    key = _key()
    async with httpx.AsyncClient() as http:
        put = await http.put(storage.presign_put(key, "image/jpeg", 900), content=b"\xff\xd8jpeg",
                             headers={"Content-Type": "image/jpeg"})
        assert put.status_code == 200, put.text
        assert await storage.head(key) == ObjectInfo(size_bytes=6, content_type="image/jpeg")
        got = await http.get(storage.presign_get(key, signing_window(datetime.now(timezone.utc), "Asia/Seoul")))
        assert (got.status_code, got.content) == (200, b"\xff\xd8jpeg")
    await storage.delete([key, _key()])   # 없는 키는 조용히 넘어간다
    assert await storage.head(key) is None


async def test_서명과_다른_형식으로_올리면_저장소가_거절한다(storage):
    key = _key()
    async with httpx.AsyncClient() as http:
        put = await http.put(storage.presign_put(key, "image/jpeg", 900), content=b"x",
                             headers={"Content-Type": "image/png"})
    assert put.status_code == 403
    assert await storage.head(key) is None


async def test_지운_객체는_읽기_URL_도_실패한다(storage):
    key = _key()
    async with httpx.AsyncClient() as http:
        await http.put(storage.presign_put(key, "image/jpeg", 900), content=b"x", headers={"Content-Type": "image/jpeg"})
        await storage.delete([key])
        got = await http.get(storage.presign_get(key, signing_window(datetime.now(timezone.utc), "Asia/Seoul")))
    assert got.status_code == 404
