import logging
import urllib.parse

from firebase_admin import storage
from google.cloud.storage import Blob

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def get_blob(bucket: str, path: str) -> Blob:  # pragma: no cover
    log.debug("Fetch blob %s from %s", path, bucket)
    return storage.bucket(bucket).get_blob(path)


def upload_file(
    bucket: str, path: str, file, content_type: str = None, cache_control: str = None
) -> None:  # pragma: no cover
    log.debug("Upload file %s of type %s to %s from file", path, content_type, bucket)
    file.seek(0)
    blob = storage.bucket(bucket).blob(path)
    blob.cache_control = cache_control
    blob.upload_from_file(file, content_type=content_type)


def upload_string(
    bucket: str, path: str, string, content_type: str = None, cache_control: str = None
) -> None:  # pragma: no cover
    log.debug("Upload file %s of type %s to %s from string", path, content_type, bucket)
    blob = storage.bucket(bucket).blob(path)
    blob.cache_control = cache_control
    blob.upload_from_string(string, content_type=content_type)


def get_public_firebase_url(bucket: str, path: str) -> str:
    return (
        "https://firebasestorage.googleapis.com/v0/b/"
        + storage.bucket(bucket).name
        + "/o/"
        + urllib.parse.quote(path, safe="")
        + "?alt=media"
    )
