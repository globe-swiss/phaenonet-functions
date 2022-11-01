import pytest

from phenoback.utils import gsecrets


@pytest.fixture(autouse=True)
def clear_cache():
    gsecrets.get_secret.cache_clear()


def test_get_secret__cache(mocker):
    assert gsecrets.get_secret.cache_info().currsize == 0
    mocker.patch("google.cloud.secretmanager.SecretManagerServiceClient")
    gsecrets.get_secret("some_key")
    gsecrets.get_secret("other_key")
    gsecrets.get_secret("some_key")
    gsecrets.get_secret("other_key")
    assert gsecrets.get_secret.cache_info().currsize == 2
    assert gsecrets.get_secret.cache_info().hits == 2
    assert gsecrets.get_secret.cache_info().misses == 2


def test_get_secret__reset(mocker):
    assert gsecrets.get_secret.cache_info().currsize == 0
    mocker.patch("google.cloud.secretmanager.SecretManagerServiceClient")
    gsecrets.get_secret("some_key")
    gsecrets.reset()
    assert gsecrets.get_secret.cache_info().misses == 0
    gsecrets.get_secret("some_key")
    assert gsecrets.get_secret.cache_info().misses == 1
