# pylint: disable=protected-access
import csv
import test
from collections import namedtuple
from io import StringIO

import pytest

import phenoback
from phenoback.functions import meteoswiss_import as meteoswiss
from phenoback.utils import data as d
from phenoback.utils import firestore as f

HASH_COLLECTION = "definitions"
HASH_DOCUMENT = "meteoswiss_import"
HASH_KEY_PREFIX = "hash_"

OBSERVATION_ID_KEY = "id"
OBSERVATION_COLLECTION = "observations"
STATION_ID_KEY = "id"
STATION_COLLECTION = "individuals"

Response = namedtuple("response", "ok text elapsed status_code")


@pytest.fixture(autouse=True)
def set_phenoyear():
    f.write_document("definitions", "config_dynamic", {"phenoyear": 2000})


@pytest.fixture
def station_data() -> str:
    with open(
        test.get_resource_path("meteoswiss_stations.csv"), encoding="utf-8"
    ) as csv_file:
        return csv_file.read()


@pytest.fixture
def observation_data() -> str:
    with open(
        test.get_resource_path("meteoswiss_observations.csv"), encoding="utf-8"
    ) as csv_file:
        return csv_file.read()


class TestCommon:
    def test_main(self, mocker, data, context):
        stations_mock = mocker.patch(
            "phenoback.functions.meteoswiss_import.process_stations"
        )
        observations_mock = mocker.patch(
            "phenoback.functions.meteoswiss_import.process_observations"
        )

        meteoswiss.main(data, context)

        stations_mock.assert_called_once()
        observations_mock.assert_called_once()

    def test_get_hash(self):
        assert meteoswiss._get_hash("string1") == meteoswiss._get_hash("string1")
        assert meteoswiss._get_hash("string1") != meteoswiss._get_hash("string2")
        try:
            meteoswiss._get_hash(None)
        except AttributeError:
            pass  # expected

    def test_set_hash(self, mocker):
        hash_key = "a_key"
        data = "some_data"
        write_mock = mocker.spy(phenoback.functions.meteoswiss_import, "write_document")
        meteoswiss._set_hash(hash_key, data)
        write_mock.assert_called_once()
        assert f.get_document(HASH_COLLECTION, HASH_DOCUMENT).get(
            f"{HASH_KEY_PREFIX}{hash_key}"
        ) == meteoswiss._get_hash(data)

    def test_load_hash(self):
        meteoswiss._set_hash("key1", "data1")
        meteoswiss._set_hash("key2", "overridden")
        meteoswiss._set_hash("key2", "data2")
        assert meteoswiss._load_hash("key1") == meteoswiss._get_hash("data1")
        assert meteoswiss._load_hash("key2") == meteoswiss._get_hash("data2")


class TestObservations:
    def test_get_observation_dicts(self, mocker, observation_data):
        mocker.patch("phenoback.functions.meteoswiss_import.get_document")
        dict_reader = csv.DictReader(StringIO(observation_data), delimiter=";")
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

    def test_process_observations__ok(self, mocker):
        response_text = "some_data"
        response_elapsed = 0.01
        process_response_mock = mocker.patch(
            "phenoback.functions.meteoswiss_import.process_observations_response",
            return_value=True,
        )
        mocker.patch(
            "phenoback.functions.meteoswiss_import.get",
            return_value=Response(
                ok=True, text=response_text, elapsed=response_elapsed, status_code=200
            ),
        )

        assert meteoswiss.process_observations()
        process_response_mock.assert_called_once_with(response_text, response_elapsed)

    def test_process_observations__nok(self, mocker):
        mocker.patch(
            "phenoback.functions.meteoswiss_import.get",
            return_value=Response(ok=False, text=None, elapsed=None, status_code="5xx"),
        )
        try:
            meteoswiss.process_observations()
        except meteoswiss.ResourceNotFoundException:
            pass  # expected

    @pytest.mark.parametrize(
        "data1, data2, is_processed_expected",
        [
            ("same", "same", False),
            ("old", "new", True),
        ],
    )
    def test_process_observations_response__cache(
        self, data1, data2, is_processed_expected
    ):
        assert meteoswiss.process_observations_response(data1, 0)
        assert (
            meteoswiss.process_observations_response(data2, 0) == is_processed_expected
        )

    @pytest.mark.parametrize(
        "old_species, new_species, expected",
        [
            ("None", ["s1", "s2"], ["s1", "s2"]),
            ([], ["s1", "s2"], ["s1", "s2"]),
            (["s1", "s2"], ["s2", "s3"], ["s1", "s2", "s3"]),
        ],
    )
    def test_update_station_species(self, old_species, new_species, expected):
        individual_id = "individual_1"
        d.write_individual(
            individual_id, {"attribute": "should stay", "station_species": old_species}
        )
        meteoswiss._update_station_species({individual_id: new_species})
        result = d.get_individual(individual_id)
        assert result["attribute"]
        assert len(result["station_species"]) == len(expected)
        assert set(result["station_species"]) == set(expected)

    def test_get_station_species(self):
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


class TestStations:
    def test_clean_station_csv(self, station_data):
        clean_data = meteoswiss._clean_station_csv(station_data)
        assert len(clean_data.splitlines()) == 4

    def test_get_individuals_dicts(self, station_data):
        clean_data = meteoswiss._clean_station_csv(station_data)
        dict_reader = csv.DictReader(StringIO(clean_data), delimiter=";")
        results = meteoswiss._get_individuals_dicts(2011, dict_reader)
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
                "type",
                "year",
            } == result.keys()
            assert result["year"] == 2011
            assert result[STATION_ID_KEY].startswith("2011_")

    def test_get_individuals_dicts__footer(self, station_data):
        clean_data = meteoswiss._clean_station_csv(station_data)
        dict_reader = csv.DictReader(StringIO(clean_data), delimiter=";")
        results = meteoswiss._get_individuals_dicts(2011, dict_reader)
        # assert the footer is ignored
        assert len(results) == 3

    def test_process_stations__ok(self, mocker):
        response_text = "some_data"
        response_elapsed = 0.01
        process_response_mock = mocker.patch(
            "phenoback.functions.meteoswiss_import.process_stations_response",
            return_value=True,
        )
        mocker.patch(
            "phenoback.functions.meteoswiss_import.get",
            return_value=Response(
                ok=True, text=response_text, elapsed=response_elapsed, status_code=200
            ),
        )

        year = 2000
        assert meteoswiss.process_stations(year)
        process_response_mock.assert_called_once_with(
            year, response_text, response_elapsed
        )

    def test_process_stations__nok(self, mocker):
        mocker.patch(
            "phenoback.functions.meteoswiss_import.get",
            return_value=Response(ok=False, text=None, elapsed=None, status_code="5xx"),
        )
        try:
            meteoswiss.process_stations(2000)
        except meteoswiss.ResourceNotFoundException:
            pass  # expected

    def test_process_stations_response__write(self, station_data):
        phenoyear = d.get_phenoyear(True)
        meteoswiss.process_stations_response(phenoyear, station_data, 0)
        station = d.get_individual(f"{phenoyear}_ADB")
        assert station is not None
        assert d.get_individual(f"{phenoyear}_ALC") is not None
        assert d.get_individual(f"{phenoyear}_ALD") is not None

        assert station["altitude"] == 1350
        assert station["geopos"] == {"lat": 46.492022, "lng": 7.561067}
        assert station["individual"] == "ADB"
        assert station["name"] == "Adelboden"
        assert station["source"] == "meteoswiss"
        assert station["user"] == "meteoswiss"
        assert station["type"] == "station"
        assert station["year"] == phenoyear

    @pytest.mark.parametrize(
        "data1, data2, is_processed_expected",
        [
            ("same", "same", False),
            ("old", "new", True),
        ],
    )
    def test_process_stations_response__cache(
        self, mocker, data1, data2, is_processed_expected
    ):
        clean_station_mock = mocker.patch(
            "phenoback.functions.meteoswiss_import._clean_station_csv",
            side_effect=[data1, data2],
        )
        assert meteoswiss.process_stations_response(2000, data1, 0)
        clean_station_mock.assert_called_once_with(data1)
        assert (
            meteoswiss.process_stations_response(2000, data2, 0)
            == is_processed_expected
        )

    def test_process_stations_response__cache_year_change(self):
        data = "some_data"
        assert meteoswiss.process_stations_response(2000, data, 0)
        assert not meteoswiss.process_stations_response(2000, data, 0)
        assert meteoswiss.process_stations_response(2001, data, 0)
