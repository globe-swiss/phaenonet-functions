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


def get_changepayload(initialdata, year, individual, key, value):
    data = {individual: initialdata[individual].copy()}
    data[individual][key] = value
    return {"year": year, "values": data}


def test_function_name(gcf_names):
    assert pheno_map.FUNCTION_NAME in gcf_names


def test_client(mocker):
    task_mock = mocker.patch("phenoback.utils.tasks.GCFClient")

    pheno_map.client()

    task_mock.assert_called_with("mapupdates", pheno_map.FUNCTION_NAME)


@pytest.mark.parametrize("should_update", [True, False])
def test_enqueue_change__should_update(mocker, should_update):
    client_mock = mocker.patch("phenoback.functions.map.client")
    should_update_mock = mocker.patch(
        "phenoback.functions.map._should_update", return_value=should_update
    )

    pheno_map.enqueue_change(
        "individual_id",
        ["updated_fields"],
        "species",
        ["station_species"],
        "individual_type",
        "last_phenophase",
        {"lng": 1, "lat": 2},
        "source",
        2020,
        "deveui",
        False,
    )

    should_update_mock.assert_called_with(
        ["updated_fields"], False, ["station_species"], "last_phenophase"
    )
    if should_update:
        client_mock.return_value.send.assert_called()
    else:
        client_mock.assert_not_called()


def test_enqueue_change__values(mocker):
    client_mock = mocker.patch("phenoback.functions.map.client")
    mocker.patch("phenoback.functions.map._should_update", return_value=True)

    pheno_map.enqueue_change(
        "individual_id",
        ["updated_fields"],
        "species",
        ["station_species"],
        "individual_type",
        "last_phenophase",
        {"lng": 1, "lat": 2},
        "source",
        2020,
        "deveui",
        False,
    )

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
                    "hs": True,
                }
            },
        }
    )


def test_enqueue_change__optional_fields_delete(mocker):
    client_mock = mocker.patch("phenoback.functions.map.client")
    mocker.patch("phenoback.functions.map._should_update", return_value=True)

    pheno_map.enqueue_change(
        "individual_id",
        ["updated_fields"],
        None,
        None,
        "individual_type",
        None,
        {"lng": 1, "lat": 2},
        "source",
        2020,
        None,
        False,
    )

    client_mock.return_value.send.assert_called_with(
        {
            "year": 2020,
            "values": {
                "individual_id": {
                    "sp": pheno_map.DELETE_TOKEN,
                    "ss": pheno_map.DELETE_TOKEN,
                    "t": "individual_type",
                    "p": pheno_map.DELETE_TOKEN,
                    "g": {"lng": 1, "lat": 2},
                    "so": "source",
                    "hs": pheno_map.DELETE_TOKEN,
                }
            },
        }
    )


def test_process_change__other_individuals_unchanged(mapdata, initialdata: dict):
    changepayload = get_changepayload(
        initialdata, 2020, "individual_1", "key1", "new_value"
    )
    pheno_map.process_change(changepayload)

    result_year = f.get_document("maps", "2020")["data"]
    other_year = f.get_document("maps", "2021")["data"]

    assert result_year["individual_2"] == initialdata["individual_2"]
    assert other_year == initialdata


def test_process_change__change_value(mapdata, initialdata: dict):
    assert initialdata["individual_1"]["key1"] != "new_value"
    changepayload = get_changepayload(
        initialdata, 2020, "individual_1", "key1", "new_value"
    )
    pheno_map.process_change(changepayload)

    result_year = f.get_document("maps", "2020")["data"]

    assert result_year["individual_1"] == changepayload["values"]["individual_1"]


def test_process_change__drop_value(mapdata, initialdata: dict):
    assert initialdata["individual_1"]["key1"]
    changepayload = get_changepayload(
        initialdata, 2020, "individual_1", "key1", pheno_map.DELETE_TOKEN
    )
    pheno_map.process_change(changepayload)

    result_year = f.get_document("maps", "2020")["data"]

    changepayload["values"]["individual_1"].pop("key1")
    assert result_year["individual_1"] == changepayload["values"]["individual_1"]


def test_process_change__new_value(mapdata, initialdata: dict):
    assert not initialdata["individual_1"].get("new_key")
    changepayload = get_changepayload(
        initialdata, 2020, "individual_1", "new_key", "new_value"
    )
    pheno_map.process_change(changepayload)

    result_year = f.get_document("maps", "2020")["data"]

    assert result_year["individual_1"] == changepayload["values"]["individual_1"]


@pytest.mark.parametrize(
    "station_species, last_phenophase, expected",
    [
        (["HS"], None, True),
        (None, "BLA", True),
        (None, None, False),
    ],
)
def test_should_update__on_create(station_species, last_phenophase, expected):
    assert (
        pheno_map._should_update([], True, station_species, last_phenophase) == expected
    )


@pytest.mark.parametrize(
    "updated_fields, expected",
    [
        (["geopos.lat"], True),
        (["geopos.lng"], True),
        (["station_species"], True),
        (["species"], True),
        (["type"], True),
        (["last_phenophase"], True),
        (["source"], True),
        (["deveui"], True),
        (["source", "other_values"], True),
        (["other_values"], False),
        (["reprocess"], True),
    ],
)
def test_should_update__on_update(updated_fields, expected):
    assert pheno_map._should_update(updated_fields, False, None, None) == expected


def test_delete(mapdata):
    pheno_map.delete(2020, "individual_1")

    result_year = f.get_document("maps", "2020")["data"]
    other_year = f.get_document("maps", "2021")["data"]

    assert result_year.get("individual_1") is None, result_year
    assert result_year.get("individual_2") is not None, result_year
    assert other_year.get("individual_1") is not None, other_year
    assert other_year.get("individual_2") is not None, other_year


def test_init():
    year = 2025
    pheno_map.init(year)

    doc = f.get_document("maps", str(year))
    assert doc
    assert doc["year"] == year
    assert doc["data"] == {}
