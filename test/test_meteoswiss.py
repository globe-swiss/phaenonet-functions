import csv
from collections import namedtuple

import test

import pytest

from phenoback.functions import meteoswiss

hash_collection = 'definitions'
hash_document = 'meteoswiss_import'
hash_key_prefix = 'hash_'

observation_id_key = 'id'
observation_collection = 'observations'
station_id_key = 'id'
station_collection = 'individuals'

Response = namedtuple('response', 'ok text elapsed status_code')


def test_get_hash():
    assert meteoswiss._get_hash('string1') == meteoswiss._get_hash('string1')
    assert meteoswiss._get_hash('string1') != meteoswiss._get_hash('string2')
    try:
        meteoswiss._get_hash(None)
    except AttributeError:
        pass  # expected


def test_set_hash(mocker):
    write_mock = mocker.patch('phenoback.functions.meteoswiss.write_document')
    meteoswiss._set_hash('a_key', 'some_data')
    write_mock.assert_called_once()
    call = write_mock.call_args[0]
    assert call[0] == hash_collection  # collection
    assert call[1] == hash_document  # document
    assert len(call[2]) == 1
    assert call[2].get('%sa_key' % hash_key_prefix) == (meteoswiss._get_hash('some_data'))


@pytest.mark.parametrize('key, document, expected',
                         [('mykey', {'%smykey' % hash_key_prefix: 'myhash'}, 'myhash'),
                          ('otherkey', {'%smykey' % hash_key_prefix: 'myhash'}, None),
                          ('akey', {'%smykey' % hash_key_prefix: 'myhash',
                                    '%sakey' % hash_key_prefix: 'ahash'}, 'ahash')
                          ])
def test_load_hash(mocker, key, document, expected):
    mocker.patch('phenoback.functions.meteoswiss.get_document', return_value=document)
    assert meteoswiss._load_hash(key) == expected


def test_get_observation_dicts(mocker):
    mocker.patch('phenoback.functions.meteoswiss.get_document')
    csv_file = open(test.get_resource_path('meteoswiss_observations.csv'))
    dict_reader = csv.DictReader(csv_file, delimiter=';')
    results = meteoswiss._get_observations_dicts(dict_reader)
    # assert all keys are generated
    for result in results:
        assert {observation_id_key, 'user', 'date', 'individual_id', 'individual',
                'source', 'year', 'species', 'phenophase'} == result.keys()


@pytest.mark.parametrize('new_hash, old_hash, is_processed_expected',
                         [('hash_match', 'hash_match', False),
                          ('hash_new', 'hash_old', True),
                          ('hash_new', None, True)
                          ])
def test_process_observations_ok(mocker, new_hash, old_hash, is_processed_expected):
    response_text = 'some response text'
    mocker.patch('phenoback.functions.meteoswiss.get', return_value=Response(ok=True, text=response_text,
                                                                             elapsed=None, status_code=None))
    mocker.patch('phenoback.functions.meteoswiss._get_hash', return_value=new_hash)
    load_hash_mock = mocker.patch('phenoback.functions.meteoswiss._load_hash', return_value=old_hash)
    mocker.patch('phenoback.functions.meteoswiss._get_observations_dicts', return_value=[])
    write_batch_mock = mocker.patch('phenoback.functions.meteoswiss.write_batch')
    set_hash_mock = mocker.patch('phenoback.functions.meteoswiss._set_hash')

    assert is_processed_expected == meteoswiss.process_observations()

    if is_processed_expected:
        # check write
        write_batch_mock.assert_called_once()
        call = write_batch_mock.call_args
        assert call[0][0] == observation_collection  # collection
        assert call[0][1] == observation_id_key  # document id key
        assert call[1] == {'merge': True}
        # check hash
        set_hash_mock.assert_called_once()
        # test hash loading and writing use the same key
        assert load_hash_mock.call_args[0][0] == set_hash_mock.call_args[0][0]
        assert set_hash_mock.call_args[0][1] == response_text
    else:
        write_batch_mock.assert_not_called()
        set_hash_mock.assert_not_called()


def test_process_observations_nok(mocker):
    mocker.patch('phenoback.functions.meteoswiss.get', return_value=Response(ok=False, text=None,
                                                                             elapsed=None, status_code='5xx'))
    try:
        meteoswiss.process_observations()
    except meteoswiss.ResourceNotFoundException:
        pass  # expected


def test_get_individuals_dicts(mocker):
    phenoyear_mock = mocker.patch('phenoback.functions.meteoswiss.get_phenoyear', return_value=2011)
    csv_file = open(test.get_resource_path('meteoswiss_stations.csv'))
    dict_reader = csv.DictReader(csv_file, delimiter=';')
    results = meteoswiss._get_individuals_dicts(dict_reader)
    # assert all keys are generated
    for result in results:
        assert {station_id_key, 'altitude', 'geopos', 'individual', 'name',
                'source', 'user', 'year'} == result.keys()
        assert result['year'] == 2011
        assert result[station_id_key].startswith('2011_')
    phenoyear_mock.assert_called_once()


def test_get_individuals_dicts_footer(mocker):
    mocker.patch('phenoback.functions.meteoswiss.get_phenoyear', return_value=2011)
    csv_file = open(test.get_resource_path('meteoswiss_stations.csv'))
    dict_reader = csv.DictReader(csv_file, delimiter=';')
    results = meteoswiss._get_individuals_dicts(dict_reader)
    # assert the footer is ignored
    assert len(results) == 3


@pytest.mark.parametrize('new_hash, old_hash, is_processed_expected',
                         [('hash_match', 'hash_match', False),
                          ('hash_new', 'hash_old', True),
                          ('hash_new', None, True)
                          ])
def test_process_stations_ok(mocker, new_hash, old_hash, is_processed_expected):
    mocker.patch('phenoback.functions.meteoswiss.get_phenoyear', return_value=2011)
    response_text = 'some response text'
    mocker.patch('phenoback.functions.meteoswiss.get', return_value=Response(ok=True, text=response_text,
                                                                             elapsed=None, status_code=None))
    mocker.patch('phenoback.functions.meteoswiss._get_hash', return_value=new_hash)
    load_hash_mock = mocker.patch('phenoback.functions.meteoswiss._load_hash', return_value=old_hash)
    mocker.patch('phenoback.functions.meteoswiss._get_observations_dicts', return_value=[])
    write_batch_mock = mocker.patch('phenoback.functions.meteoswiss.write_batch')
    set_hash_mock = mocker.patch('phenoback.functions.meteoswiss._set_hash')

    assert is_processed_expected == meteoswiss.process_stations()

    if is_processed_expected:
        # check write
        write_batch_mock.assert_called_once()
        call = write_batch_mock.call_args
        assert call[0][0] == station_collection  # collection
        assert call[0][1] == station_id_key  # document id key
        assert call[1] == {'merge': True}
        # check hash
        set_hash_mock.assert_called_once()
        # test hash loading and writing use the same key
        assert load_hash_mock.call_args[0][0] == set_hash_mock.call_args[0][0]
        assert set_hash_mock.call_args[0][1] == response_text
    else:
        write_batch_mock.assert_not_called()
        set_hash_mock.assert_not_called()


def test_process_stations_nok(mocker):
    mocker.patch('phenoback.functions.meteoswiss.get', return_value=Response(ok=False, text=None,
                                                                             elapsed=None, status_code='5xx'))
    try:
        meteoswiss.process_stations()
    except meteoswiss.ResourceNotFoundException:
        pass  # expected
