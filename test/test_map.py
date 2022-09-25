# pylint: disable=unused-argument,protected-access
import pytest

from phenoback.functions import map as pheno_map
from phenoback.utils import firestore as f


@pytest.fixture
def initialdata():
    return {
        "individual_1": {"key1": "value1", "key2": "value2"},
        "individual_2": {"key1": "value1", "key2": "value2"},
    }


@pytest.fixture
def mapdata(initialdata):
    f.write_document(
        "maps",
        "2020",
        {"data": initialdata},
    )
    f.write_document(
        "maps",
        "2021",
        {"data": initialdata},
    )


@pytest.fixture
def changepayload():
    return {"year": 2020, "values": {"individual_1": {"key1": "change1"}}}


def test_client(mocker):
    task_mock = mocker.patch("phenoback.utils.tasks.HTTPClient")

    pheno_map.client()

    task_mock.assert_called_with("mapupdates", "process_individual_map")


@pytest.mark.parametrize("should_update", [True, False])
def test_enqueue_change(mocker, should_update):
    client_mock = mocker.patch("phenoback.functions.map.client")
    should_update_mock = mocker.patch(
        "phenoback.functions.map._should_update", return_value=should_update
    )

    pheno_map.enqueue_change(
        "individual_id",
        "species",
        ["station_species"],
        "individual_type",
        "last_phenophase",
        {"lng": 1, "lat": 2},
        "source",
        2020,
        ["updated_fields"],
    )

    assert should_update_mock.called_with(["updated_fields"])
    if should_update:
        client_mock.return_value.send.assert_called_with(
            {
                "year": 2020,
                "values": {
                    "individual_id": {
                        "sp": "species",
                        "ss": ["station_species"],
                        "t": "individual_type",
                        "p": "last_phenophase",
                        "g": {"lng": 1, "lat": 2},
                        "so": "source",
                    }
                },
            }
        )
    else:
        client_mock.assert_not_called()


def test_process_change(mapdata, changepayload, initialdata):
    pheno_map.process_change(changepayload)

    result_year = f.get_document("maps", "2020")["data"]
    other_year = f.get_document("maps", "2021")["data"]

    assert (
        changepayload["values"]["individual_1"].items()
        <= result_year["individual_1"].items()
    )
    assert result_year["individual_2"] == initialdata["individual_2"]
    assert other_year == initialdata


@pytest.mark.parametrize(
    "updated_fields, expected",
    [
        (["geopos.lat"], True),
        (["geopos.lng"], True),
        (["station_species"], True),
        (["last_phenophase"], True),
        (["source"], True),
        (["source", "other_values"], True),
        (["other_values"], False),
    ],
)
def test_should_update(updated_fields, expected):
    assert pheno_map._should_update(updated_fields) == expected


def test_delete(mapdata):
    pheno_map.delete(2020, "individual_1")

    result_year = f.get_document("maps", "2020")["data"]
    other_year = f.get_document("maps", "2021")["data"]

    assert result_year.get("individual_1") is None, result_year
    assert result_year.get("individual_2") is not None, result_year
    assert other_year.get("individual_1") is not None, other_year
    assert other_year.get("individual_2") is not None, other_year
