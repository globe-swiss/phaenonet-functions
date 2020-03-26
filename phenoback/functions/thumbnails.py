import os
from phenoback.gcloud.utils import *
from PIL import Image


def process_new_image(bucket: str, pathfile: str) -> bool:
    path = os.path.split(pathfile)[0]
    filename_base = os.path.splitext(os.path.split(pathfile)[1])[0]
    filename_ext = os.path.splitext(pathfile)[1]

    if path.startswith('images/') and not filename_base.endswith('_tn'):
        print('DEBUG: processing thumbnail for %s' % pathfile)
        img_in = download_file(bucket, pathfile)
        img = Image.open(img_in)
        img.thumbnail((476, 302))
        img_out = tempfile.TemporaryFile()
        img.save(img_out, 'JPEG')

        upload_file(bucket, '%s/%s_tn%s' % (path, filename_base, filename_ext), img_out, content_type='image/jpeg')
        return True
    else:
        print('DEBUG: skipping thumbnail creation for %s' % pathfile)
        return False