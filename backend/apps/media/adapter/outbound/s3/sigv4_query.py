"""S3 읽기 URL 의 SigV4 쿼리 서명 — 서명 시각을 직접 정한다.

botocore 는 서명 시각을 늘 '지금'으로 찍어서 같은 객체의 URL 이 호출마다 바뀐다. 하루 동안 같은 URL 을 주려면
(설계 7.3) 서명 시각을 창의 시작으로 고정해야 해서 GET 서명만 여기서 만든다. 결과는 botocore 가 같은 시각에
만드는 URL 과 글자까지 같다(`test_sigv4_query.py`). 경로 방식 주소(https://호스트/버킷/키)를 쓴다.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from urllib.parse import quote, urlsplit

_ALGORITHM = "AWS4-HMAC-SHA256"


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def presign_get_url(
    endpoint: str, bucket: str, key: str, region: str, access_key: str, secret_key: str,
    signed_at: datetime, expires_in_seconds: int,
) -> str:
    host = urlsplit(endpoint).netloc
    amz_date = signed_at.strftime("%Y%m%dT%H%M%SZ")
    day = signed_at.strftime("%Y%m%d")
    scope = f"{day}/{region}/s3/aws4_request"
    path = "/" + quote(bucket, safe="") + "/" + quote(key, safe="/~")
    query = (
        f"X-Amz-Algorithm={_ALGORITHM}"
        f"&X-Amz-Credential={quote(f'{access_key}/{scope}', safe='')}"
        f"&X-Amz-Date={amz_date}"
        f"&X-Amz-Expires={expires_in_seconds}"
        "&X-Amz-SignedHeaders=host"
    )
    canonical = "\n".join(["GET", path, query, f"host:{host}", "", "host", "UNSIGNED-PAYLOAD"])
    string_to_sign = "\n".join([_ALGORITHM, amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    signing_key = _hmac(_hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), day), region), "s3"), "aws4_request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return f"{endpoint.rstrip('/')}{path}?{query}&X-Amz-Signature={signature}"
