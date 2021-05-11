import logging
import os
from io import BytesIO

import tinify

from phenoback.utils import gsecrets
from phenoback.utils.storage import get_public_firebase_url, upload_file

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

THUMBNAIL_WIDTH = 302
THUMBNAIL_HEIGHT = 302


def process_new_image(pathfile: str, bucket=None) -> bool:
    path = os.path.split(pathfile)[0]
    filename_base = os.path.splitext(os.path.split(pathfile)[1])[0]
    filename_ext = os.path.splitext(pathfile)[1]

    if path.startswith("images/") and not filename_base.endswith("_tn"):
        log.debug("creating thumbnail for %s", pathfile)
        setkey()

        thumbnail_file = get_thumbnail(
            get_public_firebase_url(bucket, pathfile),
            width=THUMBNAIL_WIDTH,
            height=THUMBNAIL_HEIGHT,
        )
        upload_file(
            bucket,
            "%s/%s_tn%s" % (path, filename_base, filename_ext),
            thumbnail_file,
            content_type="image/jpeg",
            cache_control="public, max-age=31536000",
        )
        return True
    else:
        log.debug("skipping thumbnail creation for %s", pathfile)
        return False


def get_thumbnail(url: str, width: int, height: int) -> BytesIO:
    log.debug("tinifying url %s", url)
    source = tinify.from_url(url)  # pylint: disable=no-member
    resized = source.resize(method="cover", width=width, height=height)
    return BytesIO(resized.to_buffer())


def setkey():
    try:
        tinify.key = gsecrets.get_tinify_apikey()
        tinify.validate()  # pylint: disable=no-member
    except tinify.Error:
        log.warning("Tinify key failed - dropping secret cache, retrying")
        gsecrets.reset()
        tinify.key = gsecrets.get_tinify_apikey()
