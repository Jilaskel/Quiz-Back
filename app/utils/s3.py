import boto3
from botocore.client import Config as BotoConfig
from app.core.config import settings

def make_s3_client(endpoint_url: str):
    cfg = BotoConfig(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_KEY,
        aws_secret_access_key=settings.S3_SECRET,
        config=cfg,
        use_ssl=endpoint_url.startswith("https"),
    )

def make_s3_internal():
    return make_s3_client(str(settings.S3_ENDPOINT))

def make_s3_public():
    return make_s3_client(str(settings.MINIO_PUBLIC_ENDPOINT))

def presign_get_url(s3, *, bucket: str, key: str, content_type: str, ttl: int) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key, "ResponseContentType": content_type},
        ExpiresIn=ttl,
    )