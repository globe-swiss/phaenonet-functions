# pylint: disable=protected-access
import csv
import test
from collections import namedtuple

import pytest

from phenoback.functions import meteoswiss_import as meteoswiss
from phenoback.utils.data import get_individual, write_individual

HASH_COLLECTION = "definitions"
HASH_DOCUMENT = "meteoswiss_import"
HASH_KEY_PREFIX = "hash_"

OBSERVATION_ID_KEY = "id"
OBSERVATION_COLLECTION = "observations"
STATION_ID_KEY = "id"
STATION_COLLECTION = "individuals"

Response = namedtuple("response", "ok text elapsed status_code")


def test_get_hash():
    assert meteoswiss._get_hash("string1") == meteoswiss._get_hash("string1")
    assert meteoswiss._get_hash("string1") != meteoswiss._get_hash("string2")
    try:
        meteoswiss._get_hash(None)
    except AttributeError:
        pass  # expected


def test_set_hash(mocker):
    write_mock = mocker.patch("phenoback.functions.meteoswiss_import.write_document")
    meteoswiss._set_hash("a_key", "some_data")
    write_mock.assert_called_once()
    call = write_mock.call_args[0]
    assert call[0] == HASH_COLLECTION  # collection
    assert call[1] == HASH_DOCUMENT  # document
    assert len(call[2]) == 1
    assert call[2].get("%sa_key" % HASH_KEY_PREFIX) == (
        meteoswiss._get_hash("some_data")
    )


@pytest.mark.parametrize(
    "key, document, expected",
    [
        ("mykey", {"%smykey" % HASH_KEY_PREFIX: "myhash"}, "myhash"),
        ("otherkey", {"%smykey" % HASH_KEY_PREFIX: "myhash"}, None),
        (
            "akey",
            {
                "%smykey" % HASH_KEY_PREFIX: "myhash",
                "%sakey" % HASH_KEY_PREFIX: "ahash",
            },
            "ahash",
        ),
    ],
)
def test_load_hash(mocker, key, document, expected):
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get_document", return_value=document
    )
    assert meteoswiss._load_hash(key) == expected


def test_get_observation_dicts(mocker):
    mocker.patch("phenoback.functions.meteoswiss_import.get_document")
    csv_file = open(test.get_resource_path("meteoswiss_observations.csv"))
    dict_reader = csv.DictReader(csv_file, delimiter=";")
    results = meteoswiss._get_observations_dicts(dict_reader)
    # assert all keys are generated
    for result in results:
        assert {
            OBSERVATION_ID_KEY,
            "user",
            "date",
            "individual_id",
            "individual",
            "source",
            "year",
            "species",
            "phenophase",
        } == result.keys()


@pytest.mark.parametrize(
    "new_hash, old_hash, is_processed_expected",
    [
        ("hash_match", "hash_match", False),
        ("hash_new", "hash_old", True),
        ("hash_new", None, True),
    ],
)
def test_process_observations_ok(mocker, new_hash, old_hash, is_processed_expected):
    response_text = "some response text"
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get",
        return_value=Response(
            ok=True, text=response_text, elapsed=None, status_code=None
        ),
    )
    mocker.patch(
        "phenoback.functions.meteoswiss_import._get_hash", return_value=new_hash
    )
    load_hash_mock = mocker.patch(
        "phenoback.functions.meteoswiss_import._load_hash", return_value=old_hash
    )
    mocker.patch(
        "phenoback.functions.meteoswiss_import._get_observations_dicts",
        return_value=[],
    )
    write_batch_mock = mocker.patch("phenoback.functions.meteoswiss_import.write_batch")
    set_hash_mock = mocker.patch("phenoback.functions.meteoswiss_import._set_hash")

    assert is_processed_expected == meteoswiss.process_observations()

    if is_processed_expected:
        # check write
        write_batch_mock.assert_called_once()
        call = write_batch_mock.call_args
        assert call[0][0] == OBSERVATION_COLLECTION  # collection
        assert call[0][1] == OBSERVATION_ID_KEY  # document id key
        assert call[1] == {"merge": True}
        # check hash
        set_hash_mock.assert_called_once()
        # test hash loading and writing use the same key
        assert load_hash_mock.call_args[0][0] == set_hash_mock.call_args[0][0]
        assert set_hash_mock.call_args[0][1] == response_text
    else:
        write_batch_mock.assert_not_called()
        set_hash_mock.assert_not_called()


def test_process_observations_nok(mocker):
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get",
        return_value=Response(ok=False, text=None, elapsed=None, status_code="5xx"),
    )
    try:
        meteoswiss.process_observations()
    except meteoswiss.ResourceNotFoundException:
        pass  # expected


def test_get_individuals_dicts(mocker):
    phenoyear_mock = mocker.patch(
        "phenoback.functions.meteoswiss_import.get_phenoyear", return_value=2011
    )
    csv_file = open(test.get_resource_path("meteoswiss_stations.csv"))
    dict_reader = csv.DictReader(csv_file, delimiter=";")
    results = meteoswiss._get_individuals_dicts(dict_reader)
    # assert all keys are generated
    for result in results:
        assert {
            STATION_ID_KEY,
            "altitude",
            "geopos",
            "individual",
            "name",
            "source",
            "user",
            "year",
        } == result.keys()
        assert result["year"] == 2011
        assert result[STATION_ID_KEY].startswith("2011_")
    phenoyear_mock.assert_called_once()


def test_get_individuals_dicts_footer(mocker):
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get_phenoyear", return_value=2011
    )
    csv_file = open(test.get_resource_path("meteoswiss_stations.csv"))
    dict_reader = csv.DictReader(csv_file, delimiter=";")
    results = meteoswiss._get_individuals_dicts(dict_reader)
    # assert the footer is ignored
    assert len(results) == 3


@pytest.mark.parametrize(
    "new_hash, old_hash, is_processed_expected",
    [
        ("hash_match", "hash_match", False),
        ("hash_new", "hash_old", True),
        ("hash_new", None, True),
    ],
)
def test_process_stations_ok(mocker, new_hash, old_hash, is_processed_expected):
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get_phenoyear", return_value=2011
    )
    response_text = "some response text"
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get",
        return_value=Response(
            ok=True, text=response_text, elapsed=None, status_code=None
        ),
    )
    mocker.patch(
        "phenoback.functions.meteoswiss_import._get_hash", return_value=new_hash
    )
    load_hash_mock = mocker.patch(
        "phenoback.functions.meteoswiss_import._load_hash", return_value=old_hash
    )
    mocker.patch(
        "phenoback.functions.meteoswiss_import._get_observations_dicts", return_value=[]
    )
    write_batch_mock = mocker.patch("phenoback.functions.meteoswiss_import.write_batch")
    set_hash_mock = mocker.patch("phenoback.functions.meteoswiss_import._set_hash")

    assert is_processed_expected == meteoswiss.process_stations()

    if is_processed_expected:
        # check write
        write_batch_mock.assert_called_once()
        call = write_batch_mock.call_args
        assert call[0][0] == STATION_COLLECTION  # collection
        assert call[0][1] == STATION_ID_KEY  # document id key
        assert call[1] == {"merge": True}
        # check hash
        set_hash_mock.assert_called_once()
        # test hash loading and writing use the same key
        assert load_hash_mock.call_args[0][0] == set_hash_mock.call_args[0][0]
        assert set_hash_mock.call_args[0][1] == response_text
    else:
        write_batch_mock.assert_not_called()
        set_hash_mock.assert_not_called()


def test_process_stations_nok(mocker):
    mocker.patch(
        "phenoback.functions.meteoswiss_import.get",
        return_value=Response(ok=False, text=None, elapsed=None, status_code="5xx"),
    )
    try:
        meteoswiss.process_stations()
    except meteoswiss.ResourceNotFoundException:
        pass  # expected


def test_get_station_species():
    result = meteoswiss._get_station_species(
        # output of meteoswiss._get_observations_dict
        [
            {"individual_id": "individual_1", "species": "species_1"},
            {"individual_id": "individual_1", "species": "species_2"},
            {"individual_id": "individual_2", "species": "species_1"},
        ]
    )
    assert result == {
        "individual_1": ["species_1", "species_2"],
        "individual_2": ["species_1"],
    }


@pytest.mark.parametrize(
    "old_species, new_species, expected",
    [
        ("None", ["s1", "s2"], ["s1", "s2"]),
        ([], ["s1", "s2"], ["s1", "s2"]),
        (["s1", "s2"], ["s2", "s3"], ["s1", "s2", "s3"]),
    ],
)
def test_update_station_species(old_species, new_species, expected):
    individual_id = "individual_1"
    write_individual(
        individual_id, {"attribute": "should stay", "station_species": old_species}
    )
    meteoswiss._update_station_species({individual_id: new_species})
    result = get_individual(individual_id)
    assert result["attribute"]
    assert len(result["station_species"]) == len(expected)
    assert set(result["station_species"]) == set(expected)
