"""media 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import (
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PUBLIC_ENDPOINT_URL,
    S3_REGION,
    S3_SECRET_KEY,
)
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.adapter.outbound.s3.boto3_object_storage_adapter import Boto3ObjectStorageAdapter
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_media_repository(db: AsyncSession) -> MediaRepository:
    return MediaPgRepository(db)


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStoragePort:
    """프로세스에 하나 — boto3 클라이언트는 만들기 비싸고 스레드 사이에 나눠 써도 된다. 테스트는 이 의존성을 바꿔 끼운다."""
    return Boto3ObjectStorageAdapter(S3_ENDPOINT_URL, S3_PUBLIC_ENDPOINT_URL, S3_BUCKET, S3_REGION, S3_ACCESS_KEY,
                                     S3_SECRET_KEY)
