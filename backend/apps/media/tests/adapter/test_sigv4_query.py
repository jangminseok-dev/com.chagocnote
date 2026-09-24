"""직접 만든 읽기 서명이 botocore 가 같은 시각에 만드는 URL 과 글자까지 같은지."""
from datetime import datetime, timezone

import boto3
import botocore.auth
from botocore.config import Config

from media.adapter.outbound.s3.sigv4_query import presign_get_url

SIGNED_AT = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)   # 서울 04:00


def _botocore_url(monkeypatch, endpoint, key):
    monkeypatch.setattr(botocore.auth, "get_current_datetime", lambda: SIGNED_AT)
    client = boto3.client("s3", endpoint_url=endpoint, region_name="ap-northeast-2", aws_access_key_id="AKIDEXAMPLE",
                          aws_secret_access_key="secret/key+value",
                          config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    return client.generate_presigned_url("get_object", Params={"Bucket": "chagocnote-media", "Key": key},
                                         ExpiresIn=172800)


def _ours(endpoint, key):
    return presign_get_url(endpoint, "chagocnote-media", key, "ap-northeast-2", "AKIDEXAMPLE", "secret/key+value",
                           SIGNED_AT, 172800)


def test_botocore_와_같은_URL_이다(monkeypatch):
    for endpoint in ("https://s3.ap-northeast-2.amazonaws.com", "http://127.0.0.1:9010"):
        for key in ("thumb/shops/1/42.jpg", "original-video/shops/12/9007199254740993.mp4"):
            assert _ours(endpoint, key) == _botocore_url(monkeypatch, endpoint, key), (endpoint, key)


def test_같은_창이면_같은_URL_이다():
    assert _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg") == _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg")
