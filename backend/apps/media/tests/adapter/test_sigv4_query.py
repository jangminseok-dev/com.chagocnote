"""직접 만든 읽기 서명이 botocore 가 같은 시각에 만드는 URL 과 글자까지 같은지."""
from datetime import datetime, timezone

import boto3
import botocore.auth
from botocore.config import Config

from media.adapter.outbound.s3.sigv4_query import presign_get_url

SIGNED_AT = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)   # 서울 04:00


DOWNLOAD = 'attachment; filename="chagocnote-42.jpg"'


def _botocore_url(monkeypatch, endpoint, key, **params):
    monkeypatch.setattr(botocore.auth, "get_current_datetime", lambda: SIGNED_AT)
    client = boto3.client("s3", endpoint_url=endpoint, region_name="ap-northeast-2", aws_access_key_id="AKIDEXAMPLE",
                          aws_secret_access_key="secret/key+value",
                          config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    return client.generate_presigned_url("get_object", Params={"Bucket": "chagocnote-media", "Key": key, **params},
                                         ExpiresIn=172800)


def _ours(endpoint, key, content_disposition=None):
    return presign_get_url(endpoint, "chagocnote-media", key, "ap-northeast-2", "AKIDEXAMPLE", "secret/key+value",
                           SIGNED_AT, 172800, content_disposition)


def test_botocore_와_같은_URL_이다(monkeypatch):
    for endpoint in ("https://s3.ap-northeast-2.amazonaws.com", "http://127.0.0.1:9010"):
        for key in ("thumb/shops/1/42.jpg", "original-video/shops/12/9007199254740993.mp4"):
            assert _ours(endpoint, key) == _botocore_url(monkeypatch, endpoint, key), (endpoint, key)


def test_같은_창이면_같은_URL_이다():
    assert _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg") == _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg")


def test_내려받기_서명도_botocore_와_같은_URL_이다(monkeypatch):
    for endpoint in ("https://s3.ap-northeast-2.amazonaws.com", "http://127.0.0.1:9010"):
        ours = _ours(endpoint, "original/shops/1/42.jpg", DOWNLOAD)
        assert ours == _botocore_url(monkeypatch, endpoint, "original/shops/1/42.jpg",
                                     ResponseContentDisposition=DOWNLOAD), endpoint
        # 공백은 %20, 세미콜론·등호·따옴표도 인코딩한다(RFC 3986).
        assert "response-content-disposition=attachment%3B%20filename%3D%22chagocnote-42.jpg%22" in ours


def test_내려받기_서명은_읽기_서명과_다르다():
    plain = _ours("http://127.0.0.1:9010", "original/shops/1/42.jpg")
    download = _ours("http://127.0.0.1:9010", "original/shops/1/42.jpg", DOWNLOAD)
    assert plain.rsplit("=", 1)[1] != download.rsplit("=", 1)[1]
