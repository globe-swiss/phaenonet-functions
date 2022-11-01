import pytest

from phenoback.functions import thumbnails


def url(path: str):
    return (
        "https://firebasestorage.googleapis.com/v0/b/bucket/o/"
        + path.replace("/", "%2f")
        + "?alt=media"
    )


@pytest.mark.parametrize(
    "image_path",
    ["images/user_id/individuals/test.jpeg", "images/user_id/individuals/test"],
)
def test_process_new_image_infinite_loop(mocker, image_path):
    setkey_mock = mocker.patch("phenoback.functions.thumbnails.setkey")
    get_thumbnail_mock = mocker.patch(
        "phenoback.functions.thumbnails.get_thumbnail", return_value=""
    )
    get_public_firebase_url_mock = mocker.patch(
        "phenoback.functions.thumbnails.get_public_firebase_url"
    )
    upload_file_mock = mocker.patch("phenoback.functions.thumbnails.upload_file")

    # process a image
    assert thumbnails.process_new_image(image_path, url(image_path))
    setkey_mock.assert_called()
    get_thumbnail_mock.assert_called()
    get_public_firebase_url_mock.assert_called()
    upload_file_mock.assert_called()
    written_file = upload_file_mock.call_args[0][1]
    # assert the output of the function is not processed again
    assert not thumbnails.process_new_image(
        written_file, url(written_file)
    ), written_file
