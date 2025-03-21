import logging
import urllib.parse

from firebase_admin import storage
from google.cloud.storage import Blob

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def get_blob(bucket: str, path: str) -> Blob:  # pragma: no cover
    log.debug("Fetch blob %s from %s", path, bucket)
    blob = storage.bucket(bucket).get_blob(path)
    if not blob:  # pragma: no cover
        raise ValueError(f"Blob {path} not found in {bucket}")
    return blob


def upload_file(
    bucket: str,
    path: str,
    file,
    content_type: str | None = None,
    cache_control: str | None = None,
) -> None:  # pragma: no cover
    log.debug("Upload file %s of type %s to %s from file", path, content_type, bucket)
    file.seek(0)
    blob = storage.bucket(bucket).blob(path)
    blob.cache_control = cache_control
    blob.upload_from_file(file, content_type=content_type)


def upload_string(
    bucket: str,
    path: str,
    string,
    content_type: str = "text/plain",
    cache_control: str | None = None,
) -> None:  # pragma: no cover
    log.debug("Upload file %s of type %s to %s from string", path, content_type, bucket)
    blob = storage.bucket(bucket).blob(path)
    blob.cache_control = cache_control
    blob.upload_from_string(string, content_type=content_type)


def get_public_firebase_url(bucket: str, path: str) -> str:
    bucket_name = storage.bucket(bucket).name
    if not bucket_name:  # pragma: no cover
        raise ValueError(f"Bucket {bucket} not found")
    return (
        "https://firebasestorage.googleapis.com/v0/b/"
        + bucket_name
        + "/o/"
        + urllib.parse.quote(path, safe="")
        + "?alt=media"
    )
