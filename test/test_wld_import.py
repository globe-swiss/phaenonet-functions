import io
import test
from zipfile import ZipFile

import pytest

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.functions import wld_import


@pytest.fixture()
def zippath():
    return test.get_resource_path("wld_import_test.zip")


@pytest.fixture()
def input_bytes(zippath):
    with open(zippath, "rb") as file:
        return io.BytesIO(file.read())


@pytest.fixture()
def data_loaded(input_bytes):
    with ZipFile(input_bytes, mode="r") as input_zip:
        wld_import.DATA = wld_import.load_data(input_zip)


def test_check_zip_archive(zippath):
    with ZipFile(zippath, mode="r") as zip_file:
        wld_import.check_zip_archive(zip_file)


def test_check_zip_archive__fail_files(mocker):
    zip_file_mock = mocker.Mock()
    zip_file_mock.namelist = mocker.Mock(return_value=["some_file"])
    with pytest.raises(FileNotFoundError):
        wld_import.check_zip_archive(zip_file_mock)


def test_check_file_size(input_bytes):
    wld_import.check_file_size(input_bytes)


def test_check_file_size__fail_size():
    with pytest.raises(OverflowError):
        wld_import.check_file_size(
            io.BytesIO(bytearray(wld_import.MAX_ARCHIVE_BYTES + 1))
        )


def test_check_load_data(input_bytes):
    with ZipFile(input_bytes, mode="r") as input_zip:
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
    assert f"{fieldname} not found" in caperrors.text


@pytest.mark.parametrize(
    "filename, fieldname",
    [
        ("user_id.csv", "user_id"),
        ("site.csv", "site_id"),
        ("observation_phaeno.csv", "observation_id"),
    ],
)
def test_check_data_integrity__error(data_loaded, caperrors, filename, fieldname):
    assert wld_import.DATA
    wld_import.DATA[filename][0][fieldname] = -999
    with pytest.raises(ValueError):
        wld_import.check_data_integrity()
    assert f"{fieldname} not" in caperrors.text


def test_import_data(mocker, input_bytes):
    mocker.patch("phenoback.utils.storage.download_file", return_value=input_bytes)
    d.update_phenoyear(2002)  # assume test data from 2001
    wld_import.import_data(zippath)
    assert len(f.get_collection_documents("users")) == 1
    assert len(f.get_collection_documents("individuals")) == 1
    assert len(f.get_collection_documents("observations")) == 2


def test_import_data__no_data(mocker, input_bytes):
    mocker.patch("phenoback.utils.storage.download_file", return_value=input_bytes)
    d.update_phenoyear(2021)  # assume test data from 2020
    wld_import.import_data(zippath)
    assert len(f.get_collection_documents("users")) == 1
    assert len(f.get_collection_documents("individuals")) == 0
    assert len(f.get_collection_documents("observations")) == 0
