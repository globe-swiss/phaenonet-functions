import pytest
from unittest.mock import MagicMock

from collections import namedtuple
from datetime import datetime
import firebase_admin

firebase_admin.initialize_app = MagicMock()
from phenoback.utils import glogging
glogging.init = MagicMock()
import main


Context = namedtuple('context', 'event_id, resource')
default_context = Context(event_id='ignored', resource='document_path/document_id')


@pytest.mark.parametrize('phenophase, expected',
                         [('BEA', True),
                          ('BLA', True),
                          ('BFA', True),
                          ('BVA', True),
                          ('FRA', True),
                          ('XXX', False),
                          ])
def test_process_observation_create_analytics__process_observation_called(mocker, phenophase, expected):
    po_mock = mocker.patch('phenoback.functions.analytics.process_observation')
    lo_mock = mocker.patch('phenoback.functions.observation.update_last_observation')
    mocker.patch('phenoback.functions.activity.process_observation')
    mocker.patch('main.get_field', return_value=phenophase)

    main.process_observation_create_analytics('ignored', default_context)
    assert po_mock.called == expected
    assert lo_mock.called


@pytest.mark.parametrize('phenophase, date_updated, expected',
                         [('BEA', True, True),
                          ('BLA', True, True),
                          ('BFA', True, True),
                          ('BVA', True, True),
                          ('FRA', True, True),
                          ('XXX', True, False),
                          ('BEA', False, False),
                          ('BLA', False, False),
                          ('BFA', False, False),
                          ('BVA', False, False),
                          ('FRA', False, False),
                          ('XXX', False, False),
                          ])
def test_process_observation_update_analytics__process_observation_called(mocker, phenophase, date_updated, expected):
    mock = mocker.patch('phenoback.functions.analytics.process_observation')
    mocker.patch('phenoback.functions.observation.update_last_observation')
    mocker.patch('phenoback.functions.activity.process_observation')
    mocker.patch('main.is_field_updated', return_value=date_updated)
    mocker.patch('main.get_field', return_value=phenophase)

    main.process_observation_update_analytics('ignored', default_context)
    assert mock.called == expected


@pytest.mark.parametrize('phenophase, expected',
                         [('BEA', True),
                          ('BLA', True),
                          ('BFA', True),
                          ('BVA', True),
                          ('FRA', True),
                          ('XXX', False)])
def test_process_observation_delete_analytics__process_remove_observation(mocker, phenophase, expected):
    mocker.patch('phenoback.functions.analytics.process_observation')
    mock = mocker.patch('phenoback.functions.analytics.process_remove_observation')
    mocker.patch('phenoback.functions.observation.update_last_observation')
    mocker.patch('phenoback.functions.activity.process_observation')
    mocker.patch('main.get_field', return_value=phenophase)

    main.process_observation_delete_analytics('ignored', default_context)
    assert mock.called == expected


@pytest.mark.parametrize('phenophase, is_create, date_updated, is_delete, expected',
                         [('XXX', True, False, False, True),
                          ('XXX', False, True, False, True),
                          ('XXX', False, False, True, True),
                          ('XXX', False, False, False, False),
                          ])
def test_process_observation_write_activity__process_activity_called(mocker, phenophase, is_create, date_updated,
                                                                     is_delete, expected):
    mocker.patch('phenoback.functions.analytics.process_observation')
    mocker.patch('phenoback.functions.analytics.process_remove_observation')
    mocker.patch('phenoback.functions.observation.update_last_observation')
    mock = mocker.patch('phenoback.functions.activity.process_observation')
    mocker.patch('main.is_create_event', return_value=is_create)
    mocker.patch('main.is_field_updated', return_value=date_updated)
    mocker.patch('main.is_delete_event', return_value=is_delete)
    mocker.patch('main.get_field', return_value=phenophase)

    main.process_observation_write_activity('ignored', default_context)
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
