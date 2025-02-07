# pylint: disable=unused-argument
import datetime
from test.functions.iot.sample_data import DraginoData as dd
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from phenoback.functions.iot import app
from phenoback.utils import data as d
from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g

YEAR = 2000
INDIVIDUAL = "individual"


@pytest.fixture(autouse=True)
def set_phenoyear():
    f.write_document("definitions", "config_dynamic", {"phenoyear": YEAR})


def add_individual(individual_id, individual, year, deveui=None):
    if deveui:
        data = {
            "deveui": deveui,
            "year": year,
            "individual": individual,
            "sensor": {"foo": "bar"},
        }
    else:
        data = {"year": year, "individual": individual}
    d.write_individual(individual_id, data)


@pytest.fixture
def increase_uplink_frequency_mock(mocker):
    return mocker.patch("phenoback.functions.iot.app.increase_uplink_frequency")


@pytest.fixture
def sensor_set_mock(mocker):
    return mocker.patch("phenoback.functions.iot.app.sensor_set")


@pytest.fixture
def remove_sensor_mock(mocker):
    return mocker.patch("phenoback.functions.iot.app.remove_sensor")


@pytest.fixture(autouse=True)
def set_uplink_frequency_mock(mocker):
    return mocker.patch("phenoback.functions.iot.dragino.set_uplink_frequency")


def today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def test_main(mocker, pubsub_event_data, context):
    process_mock = mocker.patch("phenoback.functions.iot.app.process_dragino")

    app.main(pubsub_event_data, context)

    process_mock.assert_called_with({"foo": "bar"})


@pytest.mark.parametrize(
    "action, data",
    [
        (
            "add",
            {
                "updateMask": {"fieldPaths": ["deveui"]},
                "oldValue": {},
                "value": {
                    "fields": {
                        "deveui": {"StringValue": "deveui_new"},
                        "individual": {"StringValue": "individual"},
                    }
                },
            },
        ),
        (
            "update",
            {
                "updateMask": {"fieldPaths": ["deveui"]},
                "oldValue": {
                    "fields": {
                        "deveui": {"StringValue": "deveui_old"},
                        "individual": {"StringValue": "individual"},
                    }
                },
                "value": {
                    "fields": {
                        "deveui": {"StringValue": "deveui_new"},
                        "individual": {"StringValue": "individual"},
                    }
                },
            },
        ),
    ],
)
def test_main_individual_updated(
    sensor_set_mock, remove_sensor_mock, data, context, action
):
    app.main_individual_updated(data, context)

    remove_sensor_mock.assert_not_called()
    sensor_set_mock.assert_called_with(
        g.get_document_id(context), "individual", "deveui_new"
    )


@pytest.mark.parametrize(
    "action, data",
    [
        (
            "delete",
            {
                "updateMask": {"fieldPaths": ["deveui"]},
                "oldValue": {
                    "fields": {
                        "deveui": {"StringValue": "deveui_old"},
                        "individual": {"StringValue": "individual"},
                    }
                },
                "value": {},
            },
        ),
    ],
)
def test_main_individual_updated__delete(
    sensor_set_mock, remove_sensor_mock, data, context, action
):
    app.main_individual_updated(data, context)

    sensor_set_mock.assert_not_called()
    remove_sensor_mock.assert_called_with(g.get_document_id(context))


def test_process_dragino__e2e(mocker):
    individual_id = "id1"
    add_individual(individual_id, "individual", YEAR, dd.DEVEUI)
    update_spy = mocker.spy(app, "update")
    app.process_dragino(dd.SAMPLE_DATA)

    result = d.get_individual(individual_id)

    update_spy.assert_called()
    assert result.get("sensor")
    assert f.get_document("sensors", individual_id)["data"].get(today())


def test_process_dragino__individual_not_found(mocker, capwarnings):
    update_spy = mocker.spy(app, "update")
    app.process_dragino(dd.SAMPLE_DATA)

    update_spy.assert_not_called()
    assert len(capwarnings.records) == 1, capwarnings.records


def test_get_individual_id():
    add_individual("id1", "ind1", 2000, deveui="deveui1")
    add_individual("id2", "ind2", 2000, deveui="deveui2")
    add_individual("id3", "ind2", 2001, deveui="deveui2")
    assert app.get_individual_id(2000, "deveui2") == "id2"


def test_get_individual_id__not_found():
    assert app.get_individual_id(2000, "unknown_deveui") is None


def test_update(mocker):
    individual_id = "id"
    update_history_mock = mocker.patch("phenoback.functions.iot.app.update_history")
    update_individual_mock = mocker.patch(
        "phenoback.functions.iot.app.update_individual"
    )

    app.update(dd.DECODED_PAYLOAD, YEAR, individual_id)

    update_history_mock.assert_called()
    update_individual_mock.assert_called()


def test_update_history__new():
    individual_id = "something"
    app.update_history(YEAR, individual_id, 1.0, 1.1, 2.0, 2.1)

    result = f.get_document("sensors", individual_id)["data"][today()]

    assert result.get("shs") == 1.0, result
    assert result.get("sts") == 1.1, result
    assert result.get("ahs") == 2.0, result
    assert result.get("ats") == 2.1, result
    assert result.get("n") == 1, result


def test_update_history__two():
    individual_id = "something"
    app.update_history(YEAR, individual_id, 1.0, 1.0, 1.0, 1.0)
    app.update_history(YEAR, individual_id, 3.0, 3.0, 3.0, 3.0)

    result = f.get_document("sensors", individual_id)["data"][today()]

    assert result.get("shs") == 4.0, result
    assert result.get("sts") == 4.0, result
    assert result.get("ahs") == 4.0, result
    assert result.get("ats") == 4.0, result
    assert result.get("n") == 2, result


@pytest.mark.parametrize(
    "data",
    [(9999, 0, 0, 0), (0, 0, 9999, 0), (0, 9999, 0, 0), (0, 0, 0, 9999)],
)
def test_update_history__invalid_data(
    data,
    caperrors,
):
    individual_id = "something"
    app.update_history(YEAR, individual_id, data[0], data[1], data[2], data[3])

    assert not f.get_document("sensors", individual_id)
    assert len(caperrors.records) == 1


def test_update_individual():
    individual_id = "ind_id"
    add_individual(individual_id, "individual", 2000)
    app.update_individual(individual_id, 1.0, 1.1, 2.0, 2.1)

    result = d.get_individual(individual_id)["sensor"]
    assert result["sh"] == 1.0
    assert result["st"] == 1.1
    assert result["ah"] == 2.0
    assert result["at"] == 2.1
    assert result["ts"]


def test_set_sensor__new(remove_sensor_mock, increase_uplink_frequency_mock):
    add_individual("id1", "ind1", 2000, deveui="deveui1")
    add_individual("id2", "ind2", 2000)

    app.sensor_set("id1", "ind1", "deveui1")

    remove_sensor_mock.assert_not_called()
    increase_uplink_frequency_mock.assert_called_with("deveui1")


def test_set_sensor__switch_individual(
    remove_sensor_mock,
    increase_uplink_frequency_mock,
):
    add_individual("id1", "ind1", 2000, deveui="deveui1")
    add_individual("id2", "ind2", 2000, deveui="deveui1")

    app.sensor_set("id2", "ind2", "deveui1")

    remove_sensor_mock.assert_called_with("id1")
    increase_uplink_frequency_mock.assert_called_with("deveui1")


def test_set_sensor__switch_year(
    remove_sensor_mock,
    increase_uplink_frequency_mock,
):
    add_individual("id1", "ind1", 1999, deveui="deveui1")
    add_individual("id2", "ind1", 2000, deveui="deveui1")

    app.sensor_set("id2", "ind2", "deveui1")

    remove_sensor_mock.assert_called_with("id1")
    increase_uplink_frequency_mock.assert_called_with("deveui1")


def test_remove_sensor():
    add_individual("id1", "ind1", 2000, deveui="deveui1")
    add_individual("id2", "ind2", 2000, deveui="deveui2")

    app.remove_sensor("id2")

    assert d.get_individual("id1")["deveui"] == "deveui1"
    assert d.get_individual("id1")["sensor"]  # not empty

    assert not d.get_individual("id2").get("deveui")  # removed
    assert not d.get_individual("id2")["sensor"]  # empty


def test_clear_sensors():
    individual_id = "id1"
    add_individual(individual_id, "individual", 2000, "some_deveui")
    add_individual("id2", "individual", 2000, "some_deveui")
    add_individual("id3", "individual", 1999, "some_deveui")
    assert d.get_individual(individual_id)["sensor"]  # has data

    result = app.clear_sensors(YEAR)

    assert result == 2
    assert not d.get_individual(individual_id)["sensor"]  # present but empty


@freeze_time(datetime.datetime(2020, 1, 1, tzinfo=ZoneInfo("Europe/Zurich")))
def test_increase_uplink_frequency(set_uplink_frequency_mock):
    app.increase_uplink_frequency(dd.DEVEUI)

    assert set_uplink_frequency_mock.call_count == 2
    set_uplink_frequency_mock.assert_any_call(dd.DEVEUI, 3600)
    set_uplink_frequency_mock.assert_any_call(
        dd.DEVEUI, 3600, datetime.datetime(2020, 1, 2, tzinfo=ZoneInfo("Europe/Zurich"))
    )


@pytest.mark.parametrize(
    "value, result",
    [(-50, True), (0, True), (50, True), (-51, False), (51, False)],
)
def test_valid_temperature(value, result):
    assert app.valid_temperature(value) == result


@pytest.mark.parametrize(
    "value, result",
    [(0, True), (50, True), (100, True), (-1, False), (101, False)],
)
def test_valid_humidity(value, result):
    assert app.valid_humidity(value) == result
