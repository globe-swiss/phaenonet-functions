from datetime import datetime
from test.functions.iot.sample_data import DraginoData as dd

import pytest

from phenoback.functions.iot import app
from phenoback.utils import data as d
from phenoback.utils import firestore as f

YEAR = 2000


@pytest.fixture(autouse=True)
def set_phenoyear():
    f.write_document("definitions", "config_dynamic", {"phenoyear": YEAR})


@pytest.fixture()
def individual_id():
    individual_id = "id"
    d.write_individual(individual_id, {"deveui": dd.DEVEUI, "year": YEAR})
    return individual_id


@pytest.fixture()
def individual_id_no_deveui():
    individual_id = "id_no_deveui"
    d.write_individual(individual_id, {"year": YEAR})
    return individual_id


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def test_process_dragino__e2e(mocker, individual_id):
    update_spy = mocker.spy(app, "update")
    app.process_dragino(dd.SAMPLE_DATA)

    result = d.get_individual(individual_id)

    update_spy.assert_called()
    assert result.get("sensor")
    assert f.get_document("sensors", individual_id)["data"].get(today())


def test_process_dragino__individual_not_found(mocker, caperrors):
    update_spy = mocker.spy(app, "update")
    app.process_dragino(dd.SAMPLE_DATA)

    update_spy.assert_not_called()
    assert len(caperrors.records) == 1, caperrors.records


def test_get_individual_id(individual_id):
    assert app.get_individual_id(YEAR, dd.DEVEUI) == individual_id


def test_get_individual_id__not_found():
    assert app.get_individual_id(YEAR, dd.DEVEUI) is None


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


def test_update_individual(individual_id):
    app.update_individual(individual_id, 1.0, 1.1, 2.0, 2.1)

    result = d.get_individual(individual_id)["sensor"]
    assert result["sh"] == 1.0
    assert result["st"] == 1.1
    assert result["ah"] == 2.0
    assert result["at"] == 2.1
    assert result["ts"]


def test_set_sensor__new(individual_id_no_deveui):
    result = app.set_sensor(individual_id_no_deveui, dd.DEVEUI)

    individual = d.get_individual(individual_id_no_deveui)

    assert result
    assert individual.get("deveui") == dd.DEVEUI


def test_set_sensor__switch(individual_id, individual_id_no_deveui):
    d.update_individual(individual_id, {"sensor": "some data"})
    init_old = d.get_individual(individual_id)
    init_new = d.get_individual(individual_id_no_deveui)
    assert init_old.get("deveui") == dd.DEVEUI
    assert init_old.get("sensor")
    assert not init_new.get("deveui")

    result = app.set_sensor(individual_id_no_deveui, dd.DEVEUI)

    individual_old = d.get_individual(individual_id)
    individual_new = d.get_individual(individual_id_no_deveui)

    assert result
    assert individual_new.get("deveui") == dd.DEVEUI
    assert not individual_old.get("deveui")
    assert not individual_old.get("sensor")


def test_set_sensor__not_found():
    result = app.set_sensor("some_id", dd.DEVEUI)

    assert not result


def test_remove_sensor(individual_id):
    d.update_individual(individual_id, {"sensor": "some data"})
    init = d.get_individual(individual_id)
    assert init.get("deveui") == dd.DEVEUI
    assert init.get("sensor")

    result = app.remove_sensor(dd.DEVEUI)

    individual = d.get_individual(individual_id)

    assert result
    assert not individual.get("deveui")
    assert not individual.get("sensor")


def test_remove_sensor__not_found():
    result = app.remove_sensor(dd.DEVEUI)
    assert not result


def test_clear_sensors(individual_id):
    d.update_individual(individual_id, {"sensor": "some data"})

    result = app.clear_sensors()

    assert result == 1
    assert not d.get_individual(individual_id).get("sensor")
