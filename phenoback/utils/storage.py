import logging
import tempfile

from firebase_admin import storage

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def download_file(bucket: str, path: str):
    log.debug('Download file %s from %s' % (path, bucket))
    blob = storage.bucket(bucket).get_blob(path)
    file = tempfile.TemporaryFile()
    if blob:
        blob.download_to_file(file)
        return file


def upload_file(bucket: str, path: str, file, content_type:str = None) -> None:
    log.debug('Upload file %s of type %s to %s' % (path, content_type, bucket))
    file.seek(0)
    storage.bucket(bucket).blob(path).upload_from_file(file, content_type=content_type)
