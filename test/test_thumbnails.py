from io import BytesIO
from test import get_resource_path

import pytest
from PIL import Image

from phenoback.functions import thumbnails


@pytest.fixture()
def image_rgba():
    file = BytesIO()
    image = Image.new("RGBA", size=(50, 50), color=(155, 0, 0))
    image.save(file, "png")
    file.name = "test.png"
    file.seek(0)
    return file


@pytest.fixture()
def image_rgb():
    file = BytesIO()
    image = Image.new("RGB", size=(50, 50), color=(155, 0, 0))
    image.save(file, "png")
    file.name = "test.png"
    file.seek(0)
    return file


def test_process_new_image_infinite_loop(mocker, image_rgb):
    mocker.patch("phenoback.functions.thumbnails.download_file", return_value=image_rgb)
    upload_file = mocker.patch("phenoback.functions.thumbnails.upload_file")

    # process a image
    assert thumbnails.process_new_image("images/user_id/individuals/test.jpeg")
    upload_file.assert_called()
    written_file = upload_file.call_args[0][1]
    # assert the output of the function is not processed again
    assert not thumbnails.process_new_image(written_file), written_file


def test_process_new_image_alpha(mocker, image_rgba):
    mocker.patch(
        "phenoback.functions.thumbnails.download_file", return_value=image_rgba
    )
    mocker.patch("phenoback.functions.thumbnails.upload_file")

    assert thumbnails.process_new_image("images/user_id/individuals/test.png")


def test_process_new_image_noext(mocker, image_rgb):
    mocker.patch("phenoback.functions.thumbnails.download_file", return_value=image_rgb)
    mocker.patch("phenoback.functions.thumbnails.upload_file")

    assert thumbnails.process_new_image("images/user_id/individuals/test")


def test_process_image_exif_tag_42034():
    assert thumbnails.process_image(get_resource_path("exif_tag_42034.jpg"))


def test_process_image_tuple_index_out_of_range():
    assert thumbnails.process_image(get_resource_path("tuple_index_out_of_range.jpg"))
