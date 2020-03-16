from datetime import datetime
import pytest
import firebase_admin
firebase_admin.initialize_app = lambda x = None, y = None: None  # mock calls to initialize firebase app
import main


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
    main.process_document_ts(data, mocker.MagicMock())
    assert update_modified_document.called == update_called, comment
