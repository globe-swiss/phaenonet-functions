import pytest
from unittest.mock import MagicMock

from collections import namedtuple
from datetime import datetime
import firebase_admin
from dateparser.timezone_parser import StaticTzInfo

firebase_admin.initialize_app = MagicMock()
from phenoback.gcloud import glogging
glogging.init = MagicMock()
import main


Context = namedtuple('context', 'event_id, resource')
default_context = Context(event_id='ignored', resource='document_path/document_id')


def test_activity_create_data(mocker):
    data = {'value': {'fields': {'individual': {'stringValue': 'individual'}, 'user': {'stringValue': 'user_id'}}}}
    mock = mocker.patch('phenoback.functions.activity.process_activity')

    main.process_activity_create(data, default_context)
    mock.assert_called_once_with('document_id', 'individual', 'user_id')


@pytest.mark.parametrize('phenophase, is_create, is_update, expected',
                         [('BEA', True, False, True),
                          ('BLA', True, False, True),
                          ('BFA', True, False, True),
                          ('BVA', True, False, True),
                          ('FRA', True, False, True),
                          ('BEA', False, True, True),
                          ('BLA', False, True, True),
                          ('BFA', False, True, True),
                          ('BVA', False, True, True),
                          ('FRA', False, True, True),
                          ('XXX', True, False, False),
                          ('XXX', False, True, False),
                          ('FRA', False, False, False),
                          ('XXX', False, False, False)
                          ])
def test_process_observation_write_process_observation_called(mocker, phenophase, is_create, is_update, expected):
    mock = mocker.patch('phenoback.functions.analytics.process_observation')
    mocker.patch('phenoback.functions.observation.update_last_observation')
    mocker.patch('main.is_create_event', return_value=is_create)
    mocker.patch('main.is_field_updated', return_value=is_update)
    mocker.patch('main.is_delete_event', return_value=False)
    mocker.patch('main.get_field', return_value=phenophase)

    main.process_observation_write('ignored', default_context)
    assert mock.called == expected


@pytest.mark.parametrize('phenophase, is_create, is_update, expected',
                         [('BEA', True, False, True),
                          ('BEA', False, True, True),
                          ('XXX', True, False, True),
                          ('XXX', False, True, True),
                          ('FRA', False, False, False),
                          ('XXX', False, False, False)
                          ])
def test_process_observation_write_update_last_observation_called(mocker, phenophase, is_create, is_update, expected):
    mocker.patch('phenoback.functions.analytics.process_observation')
    mock = mocker.patch('phenoback.functions.observation.update_last_observation')
    mocker.patch('main.is_create_event', return_value=is_create)
    mocker.patch('main.is_field_updated', return_value=is_update)
    mocker.patch('main.is_delete_event', return_value=False)
    mocker.patch('main.get_field', return_value=phenophase)

    main.process_observation_write('ignored', default_context)
    assert mock.called == expected


@pytest.mark.parametrize('update_called, data, comment',
                         [(False, {'oldValue': {}, 'value': {}}, 'invalid case'),
                          (False, {
                              'updateMask': {'fieldPaths': ['modified']},
                              'oldValue': {
                                'fields': {
                                    'modified': {'timestampValue': str(datetime.now())}}},
                              'value': {
                                 'fields': {
                                    'modified': {'timestampValue': str(datetime.now())}}
                              }}, 'update modified'),
                          (True, {
                              'updateMask': {'fieldPaths': ['other']},
                              'oldValue': {
                                  'fields': {
                                      'modified': {'timestampValue': str(datetime.now())}}},
                              'value': {
                                 'fields': {
                                    'modified': {'timestampValue': str(datetime.now())}}
                              }}, 'update sth else'),
                          (False, {
                              'oldValue': {},
                              'value': {
                                 'fields': {
                                    'modified': {'timestampValue': str(datetime.now())}}
                              }}, 'create case'),
                          (False, {
                              'oldValue': {
                                  'fields': {
                                      'modified': {'timestampValue': str(datetime.now())}}
                              },
                              'value': {}}, 'delete case')
                          ])
def test_document_ts_update(mocker, update_called, data, comment):
    update_modified_document = mocker.patch('phenoback.functions.documents.update_modified_document')
    mocker.patch('phenoback.functions.documents.update_created_document')
    main.process_document_ts_write(data, mocker.MagicMock())
    assert update_modified_document.called == update_called, comment
