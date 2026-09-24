from __future__ import annotations

import asyncio

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from media.adapter.outbound.s3.sigv4_query import presign_get_url
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.services.url_expiry import SigningWindow
from media.domain.value_objects.object_info import ObjectInfo

_PATH_STYLE = Config(signature_version="s3v4", s3={"addressing_style": "path"})


class Boto3ObjectStorageAdapter(ObjectStoragePort):
    """boto3(동기)를 스레드로 감싼다. 서명은 앱이 닿는 공개 주소로, HEAD·DELETE 는 서버가 닿는 내부 주소로 한다 —
    서명에 호스트가 들어가므로 앱에 줄 URL 은 공개 주소로 서명해야 한다(설계 7.4)."""

    def __init__(
        self, endpoint: str, public_endpoint: str, bucket: str, region: str, access_key: str, secret_key: str
    ) -> None:
        self._bucket = bucket
        self._public_endpoint = public_endpoint
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key
        credentials = dict(region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                           config=_PATH_STYLE)
        self._internal = boto3.client("s3", endpoint_url=endpoint, **credentials)
        self._public = boto3.client("s3", endpoint_url=public_endpoint, **credentials)

    def presign_put(self, key: str, content_type: str, expires_in_seconds: int) -> str:
        return self._public.generate_presigned_url(
            "put_object", Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in_seconds,
        )

    def presign_get(self, key: str, window: SigningWindow) -> str:
        return presign_get_url(
            self._public_endpoint, self._bucket, key, self._region, self._access_key, self._secret_key,
            window.signed_at, window.expires_in_seconds,
        )

    async def head(self, key: str) -> ObjectInfo | None:
        try:
            found = await asyncio.to_thread(self._internal.head_object, Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return ObjectInfo(size_bytes=found["ContentLength"], content_type=found.get("ContentType", ""))

    async def delete(self, keys: list[str]) -> None:
        if keys:
            await asyncio.to_thread(
                self._internal.delete_objects, Bucket=self._bucket,
                Delete={"Objects": [{"Key": k} for k in keys], "Quiet": True},
            )
