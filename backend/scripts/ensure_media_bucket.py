"""미디어 버킷을 만들고 수명주기 규칙을 건다(설계 7.4). 여러 번 돌려도 결과가 같다.

원본만 싼 저장 계층으로 옮긴다 — 사진·영상 원본은 30일 뒤 Standard-IA, 영상 원본은 90일 뒤 Glacier Instant
Retrieval. 표시용·썸네일은 자주 읽으므로 Standard 에 둔다. 규칙은 키 접두사로 거른다(`media_rules.object_keys`).
MinIO(개발)는 계층 이동을 받지 않아(InvalidStorageClass) 버킷만 만들고 규칙은 건너뛴다.
사용: cd infra && docker compose run --rm backend python scripts/ensure_media_bucket.py
"""
from __future__ import annotations

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from core.config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_REGION, S3_SECRET_KEY


def lifecycle_rules() -> list[dict]:
    return [
        {"ID": "photo-originals-to-ia", "Status": "Enabled", "Filter": {"Prefix": "original/"},
         "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]},
        {"ID": "video-originals-to-ia-then-glacier-ir", "Status": "Enabled", "Filter": {"Prefix": "original-video/"},
         "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"},
                         {"Days": 90, "StorageClass": "GLACIER_IR"}]},
    ]


def ensure_bucket(client, bucket: str) -> list[str]:
    """버킷이 없으면 만들고 규칙을 건다. 한 일을 문장으로 돌려준다."""
    done = []
    try:
        client.head_bucket(Bucket=bucket)
        done.append(f"버킷 {bucket} 이(가) 이미 있습니다.")
    except ClientError:
        client.create_bucket(Bucket=bucket)
        done.append(f"버킷 {bucket} 을(를) 만들었습니다.")
    try:
        client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": lifecycle_rules()})
        done.append("수명주기 규칙을 걸었습니다(원본 30일 IA, 영상 원본 90일 Glacier IR).")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "InvalidStorageClass":
            raise
        done.append("이 저장소는 계층 이동을 받지 않아 수명주기 규칙을 건너뜁니다(개발용 MinIO).")
    return done


def storage_client():
    return boto3.client(
        "s3", endpoint_url=S3_ENDPOINT_URL, region_name=S3_REGION, aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def main() -> None:
    for line in ensure_bucket(storage_client(), S3_BUCKET):
        print(line)


if __name__ == "__main__":
    main()
