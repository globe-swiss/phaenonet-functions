import pytest

from phenoback.utils import data as d, firestore as f
from phenoback.functions import rollover


@pytest.fixture()
def setup() -> None:
    """
    Setup based on rollover 2012 -> 2013.
    """
    d.write_individual('2011_1', {'individual': '1', 'source': 'globe', 'year': 2011,
                                  'last_observation_date': 'a value', 'last_phenophase': 'a value',
                                  'rolled': False, 'removed': False, 'obs': True})
    d.write_observation('1', {'individual_id': '2011_1'})

    d.write_individual('2012_2', {'individual': '2', 'source': 'globe', 'year': 2012,
                                  'last_observation_date': 'a value', 'last_phenophase': 'a value',
                                  'rolled': True, 'removed': False, 'obs': True})
    d.write_observation('2', {'individual_id': '2012_2'})

    d.write_individual('2012_3', {'individual': '3', 'source': 'globe', 'year': 2012,
                                  'rolled': True, 'removed': True, 'obs': False})

    d.write_individual('2012_4', {'individual': '4', 'source': 'meteoswiss', 'year': 2012,
                                  'last_observation_date': 'a value', 'last_phenophase': 'a value',
                                  'rolled': False, 'removed': False, 'obs': True})
    d.write_observation('4', {'individual_id': '2012_4'})

    d.write_individual('2012_5', {'individual': '5', 'source': 'meteoswiss', 'year': 2012,
                                  'rolled': False, 'removed': True, 'obs': False})
    d.write_observation('5', {'individual_id': '2012_5'})


def test_rollover_individuals__roll_amt(setup):
    individual_amt = len(list(f.get_collection('individuals').stream()))
    roll_amt = len(list(d.query_individuals('rolled', '==', True).stream()))

    rollover.rollover_individuals(2012, 2013)

    assert len(list(f.get_collection('individuals').stream())) == individual_amt + roll_amt


def test_rollover_individuals__keys(setup):
    rollover.rollover_individuals(2012, 2013)
    for individual_doc in d.query_individuals('year', '==', 2013).stream():
        assert individual_doc.id == '2013_' + individual_doc.to_dict()['individual']


def test_rollover_individuals__documents(setup):
    rollover.rollover_individuals(2012, 2013)
    for individual_doc in d.query_individuals('year', '==', 2013).stream():
        assert individual_doc.to_dict()['rolled'], individual_doc.to_dict()
        assert 'last_phenophase' not in individual_doc.to_dict(), individual_doc.to_dict()
        assert 'last_observation_date' not in individual_doc.to_dict(), individual_doc.to_dict()


def test_remove_stale_individuals__removed_amt(setup):
    individual_amt = len(list(f.get_collection('individuals').stream()))
    removed_amt = len(list(d.query_individuals('removed', '==', True).stream()))
    rollover.remove_stale_individuals(2012)
    results = list(f.get_collection('individuals').stream())
    assert len(results) == individual_amt - removed_amt, f.docs2str(results)


def test_remove_stale_individuals__documents(setup):
    rollover.remove_stale_individuals(2012)
    for individual_doc in d.query_individuals('year', '==', 2012).stream():
        assert not individual_doc.to_dict()['removed'], individual_doc.to_dict()


def test_rollover(mocker, setup):
    mocker.patch('phenoback.functions.rollover.get_phenoyear', return_value=2012)
    rollover_mock = mocker.patch('phenoback.functions.rollover.rollover_individuals')
    remove_mock = mocker.patch('phenoback.functions.rollover.remove_stale_individuals')
    update_year_mock = mocker.patch('phenoback.functions.rollover.update_phenoyear')
    rollover.rollover()
    rollover_mock.assert_called_with(2012, 2013)
    remove_mock.assert_called_with(2012)
    update_year_mock.assert_called_with(2013)
