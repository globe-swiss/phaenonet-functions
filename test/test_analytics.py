# pylint: disable=too-many-arguments
import copy
from contextlib import contextmanager
from datetime import timezone
from unittest.mock import Mock

import deepdiff
import pytest
from google.api_core.datetime_helpers import DatetimeWithNanoseconds as datetime
from google.cloud.firestore_v1.transaction import transactional

from phenoback.functions import analytics
from phenoback.utils import firestore
from phenoback.utils.firestore import get_document, write_document


def _date(i: int) -> datetime:
    return datetime(i, i, i, i, tzinfo=timezone.utc)


OBSERVATION_ID = "id"
SOURCE = "src"
SPECIES = "species"
PHASE = "phase"
YEAR = 2000
ALTITUDE_GRP = "grp"
DATE = _date(1)


def _data(write_document_mock: Mock) -> dict:
    """
    :param write_document_mock: mock of write document function
    :return: data written to firebase document
    """
    return write_document_mock.call_args[0][2]


def get_state_doc(
    source: str = SOURCE,
    species: str = SPECIES,
    year: int = YEAR,
    altitude_grp: str = ALTITUDE_GRP,
) -> dict:
    result = {"source": source, "species": species, "year": year, "state": {}}
    if altitude_grp:
        result["altitude_grp"] = altitude_grp
    return result


def add_state(state_doc: dict, phase: str, observation_id: str, date: datetime) -> dict:
    state_doc["state"].setdefault(phase, {})[observation_id] = date
    return state_doc


@pytest.fixture()
def state_doc():
    return get_state_doc()


@contextmanager
def transaction():
    transaction = firestore.get_transaction()
    yield transaction
    transaction.commit()


def read_state(
    year=YEAR, species=SPECIES, source=SOURCE, altitude_grp=ALTITUDE_GRP
) -> dict:
    return get_document(
        analytics.STATE_COLLECTION,
        analytics.get_analytics_document_id(year, species, source, altitude_grp),
    )


def read_result(
    year=YEAR, species=SPECIES, source=SOURCE, altitude_grp=ALTITUDE_GRP
) -> dict:
    return get_document(
        analytics.RESULT_COLLECTION,
        analytics.get_analytics_document_id(year, species, source, altitude_grp),
    )


def write_state(state_doc):
    write_document(
        analytics.STATE_COLLECTION,
        analytics.get_analytics_document_id(
            state_doc["year"],
            state_doc["species"],
            state_doc["source"],
            state_doc.get("altitude_grp"),
        ),
        state_doc,
    )


@pytest.mark.parametrize("altitude_grp", [None, "alt_grp"])
def test_update_state_initalized(altitude_grp):
    transactional_update_state = transactional(analytics.update_state)
    with transaction() as t:
        result_state = transactional_update_state(
            t, OBSERVATION_ID, DATE, PHASE, SOURCE, YEAR, SPECIES, altitude_grp
        )

    # check written document
    data = read_state(altitude_grp=altitude_grp)
    if altitude_grp is None:
        assert "altitude_grp" not in data
    else:
        assert data["altitude_grp"] == altitude_grp
    assert data["source"] == SOURCE
    assert data["year"] == YEAR
    assert data["species"] == SPECIES
    assert data["state"]["phase"][OBSERVATION_ID] == DATE
    # check returned state
    assert result_state[0] == DATE


@pytest.mark.parametrize(
    "obs_id, obs_date, phase, expected",
    [
        ("id1", 1, "phase1", {}),
        (
            "id1",
            2,
            "phase1",
            {
                "values_changed": {
                    "root['state']['phase1']['id1']": {
                        "new_value": _date(2),
                        "old_value": _date(1),
                    }
                }
            },
        ),
        ("id1", 1, "phase3", {"dictionary_item_added": ["root['state']['phase3']"]}),
    ],
)
def test_update_state_write(state_doc, obs_id, obs_date, phase, expected):
    add_state(state_doc, "phase1", "id1", _date(1))
    add_state(state_doc, "phase2", "id1", _date(2))
    add_state(state_doc, "phase1", "id2", _date(3))
    add_state(state_doc, "phase2", "id3", _date(4))
    base_state_ref = copy.deepcopy(state_doc)

    write_document(
        analytics.STATE_COLLECTION,
        analytics.get_analytics_document_id(
            state_doc["year"],
            state_doc["species"],
            state_doc["source"],
            state_doc.get("altitude_grp"),
        ),
        state_doc,
    )
    transactional_update_state = transactional(analytics.update_state)
    with transaction() as t:
        transactional_update_state(
            t,
            obs_id,
            _date(obs_date),
            phase,
            state_doc["source"],
            state_doc["year"],
            state_doc["species"],
            state_doc.get("altitude_grp"),
        )

    data = read_state(
        state_doc["year"],
        state_doc["species"],
        state_doc["source"],
        state_doc.get("altitude_grp"),
    )

    assert deepdiff.DeepDiff(base_state_ref, data) == expected, (
        base_state_ref,
        data,
    )


@pytest.mark.parametrize(
    "initial_state, next_state, expected",
    [
        (("id1", "phase1"), ("id1", "phase1"), 1),
        (("id1", "phase1"), ("id2", "phase1"), 2),
        (("id1", "phase1"), ("id2", "phase2"), 1),
        (("id1", "phase1"), ("id1", "phase2"), 1),
    ],
)
def test_update_state_returned_states(state_doc, initial_state, next_state, expected):
    initial_id = initial_state[0]
    initial_phase = initial_state[1]
    next_id = next_state[0]
    next_phase = next_state[1]
    add_state(state_doc, initial_phase, initial_id, DATE)

    write_state(state_doc)

    transactional_update_state = transactional(analytics.update_state)
    with transaction() as t:
        result_state = transactional_update_state(
            t,
            next_id,
            _date(2),
            next_phase,
            state_doc["source"],
            state_doc["year"],
            state_doc["species"],
            state_doc.get("altitude_grp"),
        )

    assert len(result_state) == expected, (state_doc, result_state)
    assert _date(2) in result_state


def test_update_results_no_dates():
    with transaction() as t:
        analytics.update_data(
            t,
            OBSERVATION_ID,
            _date(2),
            YEAR,
            SPECIES,
            PHASE,
            SOURCE,
            ALTITUDE_GRP,
        )

    # check the phase is present
    assert read_result()["values"][PHASE]

    with transaction() as t:
        analytics.update_result(t, [], PHASE, SOURCE, YEAR, SPECIES, ALTITUDE_GRP)

    # assert phase was deleted with the last value
    assert not read_result()["values"].get(PHASE)


@pytest.mark.parametrize(
    "state, e_min, e_max, e_median, e_q25, e_q75",
    [
        (
            [datetime(2020, 1, 1, tzinfo=timezone.utc)],
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
        ),
        (
            [
                datetime(2020, 1, 1, tzinfo=timezone.utc),
                datetime(2020, 1, 3, tzinfo=timezone.utc),
            ],
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
        ),
        (
            [
                datetime(2020, 1, 1, tzinfo=timezone.utc),
                datetime(2020, 1, 3, tzinfo=timezone.utc),
                datetime(2020, 1, 4, tzinfo=timezone.utc),
            ],
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 4, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 4, tzinfo=timezone.utc),
        ),
    ],
)
def test_update_results_calculation(state, e_min, e_max, e_median, e_q25, e_q75):
    source = "src"
    species = "species"
    phase = "phase"
    year = 2000
    altitude_grp = "grp"
    transactional_update_result = transactional(analytics.update_result)
    with transaction() as t:
        transactional_update_result(
            t, state, phase, source, year, species, altitude_grp
        )

    data = read_result()

    assert data["values"]["phase"]["min"] == e_min
    assert data["values"]["phase"]["max"] == e_max
    assert data["values"]["phase"]["median"] == e_median
    assert data["values"]["phase"]["quantile_25"] == e_q25
    assert data["values"]["phase"]["quantile_75"] == e_q75


@pytest.mark.parametrize("altitude_grp", [None, "alt_grp"])
def test_update_results_written(altitude_grp):
    with transaction() as t:
        analytics.update_result(
            t, [datetime.now()], PHASE, SOURCE, YEAR, SPECIES, altitude_grp
        )

    data = read_result(altitude_grp=altitude_grp)

    if altitude_grp is None:
        assert "altitude_grp" not in data
    else:
        assert data["altitude_grp"] == altitude_grp
    assert data["source"] == SOURCE
    assert data["year"] == YEAR
    assert data["species"] == SPECIES
    assert (
        k in data["values"]["phase"]
        for k in ["min", "max", "median", "quantile_25", "quantile_75"]
    )


def test_remove_observation(mocker, state_doc):
    update_result_mock = mocker.patch("phenoback.functions.analytics.update_result")

    state_doc["state"] = {
        "phase1": {"id": "value1", "another_id": "another_value1"},
        "phase2": {"id": "value2", "another_id": "another_value2"},
    }
    write_state(state_doc)

    with transaction() as t:
        analytics.remove_observation(
            t, "id", YEAR, SPECIES, "phase1", SOURCE, ALTITUDE_GRP
        )

    assert read_state()["state"] == {
        "phase1": {"another_id": "another_value1"},
        "phase2": {"id": "value2", "another_id": "another_value2"},
    }

    print(update_result_mock.call_args)
    assert update_result_mock.call_args[0][1] == ["another_value1"]


def test_remove_observation_last_value(mocker, state_doc):
    update_result_mock = mocker.patch("phenoback.functions.analytics.update_result")

    state_doc["state"] = {
        "phase1": {"id": "value1", "another_id": "another_value1"},
        "phase2": {"id": "value2"},
    }
    write_state(state_doc)

    with transaction() as t:
        analytics.remove_observation(
            t, "id", YEAR, SPECIES, "phase2", SOURCE, ALTITUDE_GRP
        )
    assert read_state()["state"] == {
        "phase1": {"id": "value1", "another_id": "another_value1"}
    }

    assert update_result_mock.call_args[0][1] == []


@pytest.mark.parametrize(
    "initial",
    [
        None,
        {},
        {
            "phase1": {"id": "value1", "another_id": "another_value1"},
            "phase2": {"id": "value2", "another_id": "another_value2"},
        },
    ],
)
def test_remove_data_not_exist(mocker, initial, state_doc):
    analytics.log = mocker.Mock()
    update_result_mock = mocker.patch("phenoback.functions.analytics.update_result")

    if initial:
        state_doc["state"] = initial
        write_state(state_doc)

    with transaction() as t:
        analytics.remove_observation(t, "id_not_exits", 0, "", "phase1", "")

    analytics.log.error.assert_called()
    update_result_mock.assert_not_called()


@pytest.mark.parametrize(
    "altitude, expected",
    [(100, "alt1"), (500, "alt2"), (800, "alt3"), (1000, "alt4"), (1200, "alt5")],
)
def test_get_altitude_grp(mocker, altitude, expected):
    mocker.patch(
        "phenoback.functions.analytics.get_individual",
        return_value={"altitude": altitude},
    )
    assert analytics.get_altitude_grp("ignored") == expected


@pytest.mark.parametrize("individual", [{}, None])
def test_get_altitude_grp_failure(mocker, individual):
    mocker.patch(
        "phenoback.functions.analytics.get_individual", return_value=individual
    )
    analytics.log = mocker.Mock()
    analytics.get_altitude_grp("ignored")
    analytics.log.error.assert_called()
