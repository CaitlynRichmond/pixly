import boto3
import os

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
    aws_secret_access_key=os.environ["AWS_SECRET_KEY"],
)


def s3_upload(filename, object_name, content_type):
    """Template for s3 upload"""

    s3.upload_file(
        filename,
        os.environ["AWS_BUCKET"],
        object_name,
        ExtraArgs={
            "ContentType": f"{content_type}",
        },
    )


def s3_delete(key):
    """Deletes object with key from the bucket"""

    s3.delete_object(Bucket=os.environ["AWS_BUCKET"], Key=key)
