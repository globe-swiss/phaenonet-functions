import os
from datetime import datetime, timezone
from unittest.mock import PropertyMock

import pytest
from google.api.context_pb2 import Context

from phenoback.utils.gcloud import (
    get_app_host,
    get_collection_path,
    get_document_id,
    get_field,
    is_create_event,
    is_delete_event,
    is_update_event,
)


@pytest.mark.parametrize(
    "expected, resource",
    [
        (
            "EDt26K5YIGoPe36z64vy_2020_BU_BFA",
            "projects/phaenonet/databases/(default)/documents/observations/EDt26K5YIGoPe36z64vy_2020_BU_BFA",
        ),
        (
            "5zhkvSSEUY5pRccOIAVf",
            "projects/phaenonet/databases/(default)/documents/activities/5zhkvSSEUY5pRccOIAVf",
        ),
        (
            "BES",
            "projects/phaenonet/databases/(default)/documents/definitions/individuals/species/FI/phenophases/BES",
        ),
    ],
)
def test_get_document_id(expected, resource):
    context = Context
    context.resource = PropertyMock(return_value=resource)
    assert get_document_id(context) == expected


@pytest.mark.parametrize(
    "expected, resource",
    [
        (
            "observations",
            "projects/phaenonet/databases/(default)/documents/observations/EDt26K5YIGoPe36z64vy_2020_BU_BFA",
        ),
        (
            "activities",
            "projects/phaenonet/databases/(default)/documents/activities/5zhkvSSEUY5pRccOIAVf",
        ),
        (
            "definitions/individuals/species/FI/phenophases",
            "projects/phaenonet/databases/(default)/documents/definitions/individuals/species/FI/phenophases/BES",
        ),
    ],
)
def test_get_collection_path(expected, resource):
    context = Context
    context.resource = PropertyMock(return_value=resource)
    assert get_collection_path(context) == expected


@pytest.fixture()
def request_data():
    return {
        "value": {
            "fields": {
                "date1": {"timestampValue": "2020-03-08T14:33:30.162Z"},
                "date2": {"timestampValue": "2020-03-18T23:00:00Z"},
                "individual": {"stringValue": "EDt26K5YIGoPe36z64vy"},
                "year": {"integerValue": "2020"},
                "boolTrue": {"booleanValue": True},
                "map": {"mapValue": {"fields": {"boolTrue": {"booleanValue": True}}}},
                "double": {"doubleValue": 1.5},
                "array": {
                    "arrayValue": {
                        "values": [
                            {"stringValue": "RK"},
                            {"stringValue": "BA"},
                        ]
                    }
                },
                "mixed": {
                    "mapValue": {
                        "fields": {
                            "myArray": {
                                "arrayValue": {
                                    "values": [
                                        {"booleanValue": True},
                                        {
                                            "mapValue": {
                                                "fields": {
                                                    "myString": {"stringValue": "abc"}
                                                }
                                            }
                                        },
                                    ]
                                }
                            },
                            "myBool": {"booleanValue": True},
                        }
                    }
                },
                "set": {"setValue": set()},
            }
        }
    }


@pytest.mark.parametrize(
    "expected, fieldname",
    [
        (datetime(2020, 3, 8, 14, 33, 30, 162000, tzinfo=timezone.utc), "date1"),
        (datetime(2020, 3, 18, 23, 0, tzinfo=timezone.utc), "date2"),
        ("EDt26K5YIGoPe36z64vy", "individual"),
        (2020, "year"),
        (None, "not_present"),
        (True, "boolTrue"),
        ({"boolTrue": True}, "map"),
        (1.5, "double"),
        (["RK", "BA"], "array"),
        ({"myBool": True, "myArray": [True, {"myString": "abc"}]}, "mixed"),
    ],
)
def test_get_field(expected, fieldname, request_data):
    assert get_field(request_data, fieldname) == expected


def test_get_field__invalid(request_data, caperrors):
    assert get_field(request_data, "set") == "set()"
    assert len(caperrors.records) == 1, caperrors.records


@pytest.mark.parametrize(
    "expected, data",
    [
        (True, {"oldValue": {}, "value": {"test": "create"}}),
        (False, {"oldValue": {"test": "delete"}, "value": {}}),
        (False, {"oldValue": {"test": "old"}, "value": {"test", "new"}}),
    ],
)
def test_is_create_event(expected, data):
    assert is_create_event(data) == expected


@pytest.mark.parametrize(
    "expected, data",
    [
        (False, {"oldValue": {}, "value": {"test": "create"}}),
        (False, {"oldValue": {"test": "delete"}, "value": {}}),
        (True, {"oldValue": {"test": "old"}, "value": {"test", "new"}}),
    ],
)
def test_is_update_event(expected, data):
    assert is_update_event(data) == expected


@pytest.mark.parametrize(
    "expected, data",
    [
        (False, {"oldValue": {}, "value": {"test": "create"}}),
        (True, {"oldValue": {"test": "delete"}, "value": {}}),
        (False, {"oldValue": {"test": "old"}, "value": {"test", "new"}}),
    ],
)
def test_is_delete_event(expected, data):
    assert is_delete_event(data) == expected


def test_get_app_host__project(mocker):
    mocker.patch("phenoback.utils.gcloud.get_project", return_value="myprojectname")
    assert get_app_host() == "myprojectname.web.app"


def test_get_app_host__env(mocker):
    mocker.patch("phenoback.utils.gcloud.get_project", return_value="myprojectname")
    os.environ["appHost"] = "specifichost.com"
    assert get_app_host() == "specifichost.com"
