import pytest
import pytz

from phenoback.gcloud.utils import *


@pytest.skip
@pytest.mark.parametrize('expected, context',
                         [('EDt26K5YIGoPe36z64vy_2020_BU_BFA', {'event_id': 'e0a433b0-188b-47d7-b4eb-95dd4a75f997-0', 'timestamp': '2020-03-08T14:52:13.469407Z', 'event_type': 'providers/cloud.firestore/eventTypes/document.write', 'resource': 'projects/phaenonet/databases/(default)/documents/observations/EDt26K5YIGoPe36z64vy_2020_BU_BFA'}),
                          ('5zhkvSSEUY5pRccOIAVf', {'event_id': 'c0453836-76a8-41d3-8b40-d1b42a412792-0', 'timestamp': '2020-03-08T14:52:13.646015Z', 'event_type': 'providers/cloud.firestore/eventTypes/document.create', 'resource': 'projects/phaenonet/databases/(default)/documents/activities/5zhkvSSEUY5pRccOIAVf'})
                          ])
def test_get_id(expected, context):
    assert get_id(context) == expected


@pytest.fixture()
def activity_data():
    return {'value': {'fields': {'date1': {'timestampValue': '2020-03-08T14:33:30.162Z'},
                                 'date2': {'timestampValue': '2020-03-18T23:00:00Z'},
                                 'individual': {'stringValue': 'EDt26K5YIGoPe36z64vy'},
                                 'year': {'integerValue': '2020'}}}}


@pytest.mark.parametrize('expected, fieldname',
                         [(datetime(2020, 3, 8, 14, 33, 30, 162000, tzinfo=pytz.UTC), 'date1'),
                          (datetime(2020, 3, 18, 23, 0, tzinfo=pytz.UTC), 'date2'),
                          ('EDt26K5YIGoPe36z64vy', 'individual'),
                          (2020, 'year')])
def test_get_field_activity(expected, fieldname, activity_data):
    assert get_field(activity_data, fieldname) == expected
