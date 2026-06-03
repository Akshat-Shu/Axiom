import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.interfaces.storage import StorageService

logger = logging.getLogger(__name__)


class S3StorageService(StorageService):
    """
    Concrete StorageService backed by Amazon S3.
    Uses the EC2 instance IAM role — no explicit credentials needed.
    """

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self._bucket = bucket_name
        self._region = region
        # boto3 automatically resolves credentials from EC2 instance metadata
        self._client = boto3.client("s3", region_name=region)

    def upload(self, file_key: str, data: bytes, content_type: str) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=file_key,
                Body=data,
                ContentType=content_type,
            )
            logger.info("Uploaded %s (%d bytes) to s3://%s", file_key, len(data), self._bucket)
            return file_key
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3 upload failed for key %s: %s", file_key, exc)
            raise

    def download(self, file_key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=file_key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3 download failed for key %s: %s", file_key, exc)
            raise

    def delete(self, file_key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=file_key)
            logger.info("Deleted s3://%s/%s", self._bucket, file_key)
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3 delete failed for key %s: %s", file_key, exc)
            raise

    def get_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": file_key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("Presigned URL generation failed for key %s: %s", file_key, exc)
            raise
