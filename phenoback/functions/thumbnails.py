import logging
import os
from phenoback.utils.storage import download_file, upload_file
from PIL import Image, ImageOps
import tempfile

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def process_new_image(pathfile: str, bucket: str = None) -> bool:
    path = os.path.split(pathfile)[0]
    filename_base = os.path.splitext(os.path.split(pathfile)[1])[0]
    filename_ext = os.path.splitext(pathfile)[1]

    if path.startswith("images/") and not filename_base.endswith("_tn"):
        log.debug("creating thumbnail for %s" % pathfile)
        img_in = download_file(bucket, pathfile)
        img_out = process_image(img_in)

        upload_file(
            bucket,
            "%s/%s_tn%s" % (path, filename_base, filename_ext),
            img_out,
            content_type="image/jpeg",
        )
        return True
    else:
        log.debug("skipping thumbnail creation for %s" % pathfile)
        return False


def process_image(img_in):
    img = Image.open(img_in)
    img = _remove_unprocessable_exif_info(img)
    img = img.convert("RGB")
    img = ImageOps.exif_transpose(img)
    img.thumbnail((476, 302))
    img_out = tempfile.TemporaryFile()
    img.save(img_out, "JPEG")
    return img_out


def _remove_unprocessable_exif_info(img):
    """
    Remove all exif info except orientation needed for rotating the image.
    """
    exif = img.getexif()
    for k in exif.keys():
        if k != 0x0112:
            exif.pop(k)
    new_exif = exif.tobytes()
    img.info["exif"] = new_exif
    return img
