# pylint: disable=unused-argument
import io
import test
from zipfile import ZipFile

import pytest

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.functions import wld_import


@pytest.fixture(autouse=True, scope="function")
def cache_clear():
    wld_import.site_users.cache_clear()
    wld_import.station_species.cache_clear()
    wld_import.tree_species.cache_clear()


@pytest.fixture()
def zippath():
    return test.get_resource_path("wld_import_test.zip")


@pytest.fixture()
def input_blob(mocker, zippath):
    with open(zippath, "rb") as input_file:
        file_bytes = input_file.read()
    mock = mocker.Mock()
    mock.download_as_bytes = mocker.Mock(return_value=file_bytes)
    mock.size = 10000
    return mock


@pytest.fixture()
def input_io(input_blob):
    return io.BytesIO(input_blob.download_as_bytes())


@pytest.fixture()
def data_loaded(input_io):
    with ZipFile(input_io, mode="r") as input_zip:
        wld_import.DATA = wld_import.load_data(input_zip)


def test_check_zip_archive(zippath):
    with ZipFile(zippath, mode="r") as zip_file:
        wld_import.check_zip_archive(zip_file)


def test_check_zip_archive__fail_files(mocker):
    zip_file_mock = mocker.Mock()
    zip_file_mock.namelist = mocker.Mock(return_value=["some_file"])
    with pytest.raises(FileNotFoundError):
        wld_import.check_zip_archive(zip_file_mock)


def test_check_file_size(mocker):
    blob_mock = mocker.Mock()
    blob_mock.size = wld_import.MAX_ARCHIVE_BYTES
    wld_import.check_file_size(blob_mock)


def test_check_file_size__fail_size(mocker):
    blob_mock = mocker.Mock()
    blob_mock.size = wld_import.MAX_ARCHIVE_BYTES + 1
    with pytest.raises(OverflowError):
        wld_import.check_file_size(blob_mock)


def test_check_load_data(input_io):
    with ZipFile(input_io, mode="r") as input_zip:
        data = wld_import.load_data(input_zip)
    assert wld_import.FILES == data.keys()
    for filedata in data.values():
        assert len(filedata) > 0


def test_check_data_integrity(data_loaded):
    assert wld_import.DATA
    wld_import.check_data_integrity()


@pytest.mark.parametrize(
    "filename, fieldname",
    [("user_id.csv", "user_id"), ("site.csv", "site_id")],
)
def test_check_data_integrity__empty(data_loaded, caperrors, filename, fieldname):
    assert wld_import.DATA
    wld_import.DATA[filename] = []
    with pytest.raises(ValueError):
        wld_import.check_data_integrity()
    assert f"{fieldname} not found" in caperrors.text, caperrors.text


@pytest.mark.parametrize(
    "filename, fieldname, value",
    [
        ("user_id.csv", "user_id", -1),
        ("site.csv", "site_id", -1),
        ("observation_phaeno.csv", "observation_id", -1),
        ("observation_phaeno.csv", "user_id", 200),
    ],
)
def test_check_data_integrity__error(
    data_loaded, caperrors, filename, fieldname, value
):
    assert wld_import.DATA
    wld_import.DATA[filename][0][fieldname] = value
    with pytest.raises(ValueError):
        wld_import.check_data_integrity()
    assert f"{fieldname} not" in caperrors.text, caperrors.text


def test_import_data(mocker, input_blob):
    mocker.patch("phenoback.utils.storage.get_blob", return_value=input_blob)
    d.update_phenoyear(2002)  # assume test data from 2001
    wld_import.import_data("mocked")
    assert len(f.get_collection_documents("users")) == 2
    assert len(f.get_collection_documents("individuals")) == 1
    assert len(f.get_collection_documents("observations")) == 2


def test_import_data__no_data(mocker, caperrors, input_blob):
    mocker.patch("phenoback.utils.storage.get_blob", return_value=input_blob)
    d.update_phenoyear(2021)  # assume test data from 2020
    wld_import.import_data("mocked")
    assert len(f.get_collection_documents("users")) == 2
    assert len(f.get_collection_documents("individuals")) == 0
    assert len(f.get_collection_documents("observations")) == 0
    assert len(caperrors.records) >= 1, caperrors
