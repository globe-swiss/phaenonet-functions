from phenoback.utils import storage


def test_get_public_firebase_url__bucket(mocker):
    bucket = "mybucket"
    bucket_mock = mocker.patch("firebase_admin.storage.bucket")
    bucket_mock.return_value.name = bucket
    assert (
        storage.get_public_firebase_url(bucket, "path/to/file").lower()
        == "https://firebasestorage.googleapis.com/v0/b/mybucket/o/path%2fto%2ffile?alt=media"
    )


def test_get_public_firebase_url__default_bucket(mocker):
    bucket_mock = mocker.patch("firebase_admin.storage.bucket")
    bucket_mock.return_value.name = "default_bucket"
    assert (
        storage.get_public_firebase_url(None, "path/to/file").lower()
        == "https://firebasestorage.googleapis.com/v0/b/default_bucket/o/path%2fto%2ffile?alt=media"
    )
