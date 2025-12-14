import boto3
from botocore.client import Config as BotoConfig
from app.core.config import settings

def make_s3_client():
    cfg = BotoConfig(
        signature_version="s3v4",
        s3={"addressing_style": "path"}
    )
    return boto3.client(
        "s3",
        endpoint_url=str(settings.S3_ENDPOINT),
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_KEY,
        aws_secret_access_key=settings.S3_SECRET,
        config=cfg,
        use_ssl=str(settings.S3_ENDPOINT).startswith("https"),
    )

def presign_get_url(s3, *, bucket: str, key: str, content_type: str, ttl: int) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key, "ResponseContentType": content_type},
        ExpiresIn=ttl,
    )