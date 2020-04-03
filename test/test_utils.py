from datetime import timezone
from unittest.mock import PropertyMock
import pytest
from google.api.context_pb2 import Context
from phenoback.gcloud.utils import *


@pytest.mark.parametrize('expected, resource',
                         [('EDt26K5YIGoPe36z64vy_2020_BU_BFA', 'projects/phaenonet/databases/(default)/documents/observations/EDt26K5YIGoPe36z64vy_2020_BU_BFA'),
                          ('5zhkvSSEUY5pRccOIAVf', 'projects/phaenonet/databases/(default)/documents/activities/5zhkvSSEUY5pRccOIAVf'),
                          ('BES', 'projects/phaenonet/databases/(default)/documents/definitions/individuals/species/FI/phenophases/BES')
                          ])
def test_get_document_id(expected, resource):
    context = Context
    context.resource = PropertyMock(return_value=resource)
    assert get_document_id(context) == expected


@pytest.mark.parametrize('expected, resource',
                         [('observations', 'projects/phaenonet/databases/(default)/documents/observations/EDt26K5YIGoPe36z64vy_2020_BU_BFA'),
                          ('activities', 'projects/phaenonet/databases/(default)/documents/activities/5zhkvSSEUY5pRccOIAVf'),
                          ('definitions/individuals/species/FI/phenophases', 'projects/phaenonet/databases/(default)/documents/definitions/individuals/species/FI/phenophases/BES')
                          ])
def test_get_collection_path(expected, resource):
    context = Context
    context.resource = PropertyMock(return_value=resource)
    assert get_collection_path(context) == expected


@pytest.fixture()
def activity_data():
    return {'value': {'fields': {'date1': {'timestampValue': '2020-03-08T14:33:30.162Z'},
                                 'date2': {'timestampValue': '2020-03-18T23:00:00Z'},
                                 'individual': {'stringValue': 'EDt26K5YIGoPe36z64vy'},
                                 'year': {'integerValue': '2020'}}}}


@pytest.mark.parametrize('expected, fieldname',
                         [(datetime(2020, 3, 8, 14, 33, 30, 162000, tzinfo=timezone.utc), 'date1'),
                          (datetime(2020, 3, 18, 23, 0, tzinfo=timezone.utc), 'date2'),
                          ('EDt26K5YIGoPe36z64vy', 'individual'),
                          (2020, 'year')])
def test_get_field_activity(expected, fieldname, activity_data):
    assert get_field(activity_data, fieldname) == expected


@pytest.mark.parametrize('expected, data',
                         [(True, {'oldValue': {}, 'value': {'test': 'create'}}),
                          (False, {'oldValue': {'test': 'delete'}, 'value': {}}),
                          (False, {'oldValue': {'test': 'old'}, 'value': {'test', 'new'}})
                          ])
def test_is_create_event(expected, data):
    assert is_create_event(data) == expected


@pytest.mark.parametrize('expected, data',
                         [(False, {'oldValue': {}, 'value': {'test': 'create'}}),
                          (False, {'oldValue': {'test': 'delete'}, 'value': {}}),
                          (True, {'oldValue': {'test': 'old'}, 'value': {'test', 'new'}})
                          ])
def test_is_update_event(expected, data):
    assert is_update_event(data) == expected


@pytest.mark.parametrize('expected, data',
                         [(False, {'oldValue': {}, 'value': {'test': 'create'}}),
                          (True, {'oldValue': {'test': 'delete'}, 'value': {}}),
                          (False, {'oldValue': {'test': 'old'}, 'value': {'test', 'new'}})
                          ])
def test_is_delete_event(expected, data):
    assert is_delete_event(data) == expected
