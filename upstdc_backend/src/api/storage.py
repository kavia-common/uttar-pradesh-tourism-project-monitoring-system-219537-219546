import boto3
from src.api.config import get_settings


# PUBLIC_INTERFACE
def get_s3_client():
    """Create a boto3 S3 client configured for S3-compatible storage."""
    s = get_settings()
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=s.S3_ENDPOINT_URL,
        region_name=s.S3_REGION,
        aws_access_key_id=s.S3_ACCESS_KEY_ID,
        aws_secret_access_key=s.S3_SECRET_ACCESS_KEY,
    )
    return client


# PUBLIC_INTERFACE
def upload_bytes(bucket: str, key: str, data: bytes, content_type: str) -> str:
    """Upload bytes to S3 and return public URL if configured, else s3:// path."""
    client = get_s3_client()
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    s = get_settings()
    if s.S3_PUBLIC_BASE_URL:
        return f"{s.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    return f"s3://{bucket}/{key}"
