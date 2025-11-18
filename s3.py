import os
import boto3
import tempfile
from dotenv import load_dotenv

class S3Handler:
    def __init__(self):
        load_dotenv()
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION")
        )
        self.bucket_name = os.getenv("S3_BUCKET_NAME")

    def download_file(self, s3_key: str) -> None:
        """Download a file from S3."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file_path = temp_file.name
        temp_file.close()   # allow boto3 to write

        self.s3.download_file(self.bucket_name, s3_key, temp_file_path)
        return temp_file_path