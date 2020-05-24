import pytest
from pytest import fail
from unittest.mock import Mock
import deepdiff
import copy

from phenoback.functions import analytics
from datetime import datetime


def _date(i: int) -> datetime:
    return datetime(i, i, i, i)


def _data(write_document_mock: Mock) -> dict:
    """
    :param write_document_mock: mock of write document function
    :return: data written to firebase document
    """
    return write_document_mock.call_args[0][2]


def _get_base_state_doc(source: str, species: str, year: int) -> dict:
    return {'source': source, 'species': species, 'year': year, 'state': {}}


def _add_observation_to_state_doc(state_doc: dict, phase: str, observation_id: str, date: datetime) -> dict:
    state_doc['state'].setdefault(phase, {})[observation_id] = date
    return state_doc


@pytest.fixture()
def base_state_doc():
    return _get_base_state_doc('source', 'species', 2020)


@pytest.mark.parametrize('altitude_grp', [None, 'alt_grp'])
def test_update_state_initalized(mocker, altitude_grp):
    mocker.patch('phenoback.functions.analytics.get_document', return_value=None)
    write_document_mock = mocker.patch('phenoback.functions.analytics.write_document')
    result_state = analytics.update_state('id', _date(1), 'phase', 'source', 1000, 'species', altitude_grp)

    # check written document
    write_data = _data(write_document_mock)
    if altitude_grp is None:
        assert 'altitude_grp' not in write_data
    else:
        assert write_data['altitude_grp'] == altitude_grp
    assert write_data['source'] == 'source'
    assert write_data['year'] == 1000
    assert write_data['species'] == 'species'
    assert write_data['state']['phase']['id'] == _date(1)
    # check returned state
    assert result_state[0] == _date(1)


@pytest.mark.parametrize('obs_id, obs_date, phase, expected',
                         [('id1', 1, 'phase1', {}),
                          ('id1', 2, 'phase1', {'values_changed': {"root['state']['phase1']['id1']": {'new_value': datetime(2, 2, 2, 2, 0), 'old_value': datetime(1, 1, 1, 1, 0)}}}),
                          ('id1', 1, 'phase3', {'dictionary_item_added': ["root['state']['phase3']"]})])
def test_update_state_write(mocker, base_state_doc, obs_id, obs_date, phase,  expected):
    _add_observation_to_state_doc(base_state_doc, 'phase1', 'id1', _date(1))
    _add_observation_to_state_doc(base_state_doc, 'phase2', 'id1', _date(2))
    _add_observation_to_state_doc(base_state_doc, 'phase1', 'id2', _date(3))
    _add_observation_to_state_doc(base_state_doc, 'phase2', 'id3', _date(4))
    base_state_ref = copy.deepcopy(base_state_doc)

    mocker.patch('phenoback.functions.analytics.get_document', return_value=base_state_doc)
    write_document_mock = mocker.patch('phenoback.functions.analytics.write_document')

    analytics.update_state(obs_id, _date(obs_date), phase,
                           base_state_doc['source'], base_state_doc['year'], base_state_doc['species'],
                           base_state_doc.get('altitude_grp'))

    write_data = _data(write_document_mock)
    assert deepdiff.DeepDiff(base_state_ref, write_data) == expected, (base_state_ref, write_data)


@pytest.mark.parametrize('initial_state, add_state, expected',
                         [(('id1', 'phase1'), ('id1', 'phase1'), 1),
                          (('id1', 'phase1'), ('id2', 'phase1'), 2),
                          (('id1', 'phase1'), ('id2', 'phase2'), 1),
                          (('id1', 'phase1'), ('id1', 'phase2'), 1)])
def test_update_state_returned_states(mocker, base_state_doc, initial_state, add_state, expected):
    initial_id = initial_state[0]
    initial_phase = initial_state[1]
    add_id = add_state[0]
    add_phase = add_state[1]
    _add_observation_to_state_doc(base_state_doc, initial_phase, initial_id, _date(1))

    mocker.patch('phenoback.functions.analytics.get_document', return_value=base_state_doc)
    mocker.patch('phenoback.functions.analytics.write_document')
    result_state = analytics.update_state(add_id, _date(2), add_phase, '', 0, '')

    assert len(result_state) == expected, (base_state_doc, result_state)
    assert _date(2) in result_state


@pytest.mark.parametrize('state, e_min, e_max, e_median, e_q25, e_q75',
                         [([datetime(2020, 1, 1)],
                           datetime(2020, 1, 1), datetime(2020, 1, 1), datetime(2020, 1, 1), datetime(2020, 1, 1), datetime(2020, 1, 1)),
                          ([datetime(2020, 1, 1), datetime(2020, 1, 3)],
                           datetime(2020, 1, 1), datetime(2020, 1, 3), datetime(2020, 1, 1), datetime(2020, 1, 1), datetime(2020, 1, 3)),
                          ([datetime(2020, 1, 1), datetime(2020, 1, 3), datetime(2020, 1, 4)],
                           datetime(2020, 1, 1), datetime(2020, 1, 4), datetime(2020, 1, 3), datetime(2020, 1, 1), datetime(2020, 1, 4))])
def test_update_results_calculation(mocker, state, e_min, e_max, e_median, e_q25, e_q75):
    write_document_mock = mocker.patch('phenoback.functions.analytics.write_document')
    analytics.update_result(state, 'phase', '', 0, '', '')
    write_data = _data(write_document_mock)
    assert write_data['values']['phase']['min'] == e_min
    assert write_data['values']['phase']['max'] == e_max
    assert write_data['values']['phase']['median'] == e_median
    assert write_data['values']['phase']['quantile_25'] == e_q25
    assert write_data['values']['phase']['quantile_75'] == e_q75


@pytest.mark.parametrize('altitude_grp', [None, 'alt_grp'])
def test_update_results_written(mocker, altitude_grp):
    write_document_mock = mocker.patch('phenoback.functions.analytics.write_document')
    analytics.update_result([datetime.now()], 'phase', 'source', 10, 'species', altitude_grp)
    write_data = _data(write_document_mock)
    if altitude_grp is None:
        assert 'altitude_grp' not in write_data
    else:
        assert write_data['altitude_grp'] == altitude_grp
    assert write_data['source'] == 'source'
    assert write_data['year'] == 10
    assert write_data['species'] == 'species'
    assert write_data['source'] == 'source'
    assert (k in write_data['values']['phase'] for k in ['min', 'max', 'median', 'quantile_25', 'quantile_75'])
    assert write_document_mock.call_args[1].get('merge')


def test_remove_observation(mocker):
    inital = {'state': {
                    'phase1': {'id': 'value1', 'another_id': 'another_value1'},
                    'phase2': {'id': 'value2', 'another_id': 'another_value2'}
                    }
              }
    mocker.patch('phenoback.functions.analytics.get_document', return_value=inital)
    write_document_mock = mocker.patch('phenoback.functions.analytics.write_document')
    update_result_mock = mocker.patch('phenoback.functions.analytics.update_result')
    analytics.remove_observation('id', 0, '', 'phase1', '')
    assert _data(write_document_mock) == {'state': {
                    'phase1': {'another_id': 'another_value1'},
                    'phase2': {'id': 'value2', 'another_id': 'another_value2'}
                    }
              }
    assert update_result_mock.call_args[0][0] == ['another_value1']


def test_remove_data_not_exist(mocker):
    initial = {'state': {
                    'phase1': {'id': 'value1', 'another_id': 'another_value1'},
                    'phase2': {'id': 'value2', 'another_id': 'another_value2'}
                    }
              }
    mocker.patch('phenoback.functions.analytics.get_document', return_value=initial)
    write_document_mock = mocker.patch('phenoback.functions.analytics.write_document')
    update_result_mock = mocker.patch('phenoback.functions.analytics.update_result')
    # noinspection PyBroadException
    try:
        analytics.remove_observation('id_not_exits', 0, '', 'phase1', '')
    except Exception:
        fail()
    write_document_mock.assert_not_called()
    update_result_mock.assert_not_called()
