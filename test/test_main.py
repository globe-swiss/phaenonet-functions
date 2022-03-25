# pylint: disable=too-many-arguments, wrong-import-position
from collections import namedtuple
from datetime import datetime
from unittest.mock import MagicMock

import firebase_admin
import flask
import pytest
import sentry_sdk

from phenoback.utils import glogging

firebase_admin.initialize_app = MagicMock()
glogging.init = MagicMock()
sentry_sdk.init = MagicMock()

import main

Context = namedtuple("context", "event_id, resource")
default_context = Context(event_id="ignored", resource="document_path/document_id")


@pytest.mark.parametrize(
    "phenophase, expected",
    [
        ("BEA", True),
        ("BLA", True),
        ("BFA", True),
        ("BVA", True),
        ("FRA", True),
        ("XXX", False),
    ],
)
def test_process_observation_create_analytics__process_observation_called(
    mocker, phenophase, expected
):
    po_mock = mocker.patch("phenoback.functions.analytics.process_observation")
    lo_mock = mocker.patch("phenoback.functions.observation.updated_observation")
    mocker.patch("phenoback.functions.activity.process_observation")
    mocker.patch("main.get_field", return_value=phenophase)

    main.process_observation_create_analytics("ignored", default_context)
    assert po_mock.called == expected
    assert lo_mock.called


@pytest.mark.parametrize(
    "phenophase, date_updated, expected",
    [
        ("BEA", True, True),
        ("BLA", True, True),
        ("BFA", True, True),
        ("BVA", True, True),
        ("FRA", True, True),
        ("XXX", True, False),
        ("BEA", False, False),
        ("BLA", False, False),
        ("BFA", False, False),
        ("BVA", False, False),
        ("FRA", False, False),
        ("XXX", False, False),
    ],
)
def test_process_observation_update_analytics__process_observation_called(
    mocker, phenophase, date_updated, expected
):
    mock = mocker.patch("phenoback.functions.analytics.process_observation")
    observation_mock = mocker.patch(
        "phenoback.functions.observation.updated_observation"
    )
    mocker.patch("phenoback.functions.activity.process_observation")
    mocker.patch("main.is_field_updated", return_value=date_updated)
    mocker.patch("main.get_field", return_value=phenophase)

    main.process_observation_update_analytics("ignored", default_context)
    assert mock.called == expected
    assert observation_mock.called == date_updated


@pytest.mark.parametrize(
    "phenophase, expected",
    [
        ("BEA", True),
        ("BLA", True),
        ("BFA", True),
        ("BVA", True),
        ("FRA", True),
        ("XXX", False),
    ],
)
def test_process_observation_delete_analytics__process_remove_observation(
    mocker, phenophase, expected
):
    mocker.patch("phenoback.functions.analytics.process_observation")
    mock = mocker.patch("phenoback.functions.analytics.process_remove_observation")
    observation_mock = mocker.patch(
        "phenoback.functions.observation.removed_observation"
    )
    mocker.patch("phenoback.functions.activity.process_observation")
    mocker.patch("main.get_field", return_value=phenophase)

    main.process_observation_delete_analytics("ignored", default_context)
    assert mock.called == expected
    assert observation_mock.called


@pytest.mark.parametrize(
    "phenophase, is_create, date_updated, is_delete, expected",
    [
        ("XXX", True, False, False, True),
        ("XXX", False, True, False, True),
        ("XXX", False, False, True, True),
        ("XXX", False, False, False, False),
    ],
)
def test_process_observation_write_activity__process_activity_called(
    mocker, phenophase, is_create, date_updated, is_delete, expected
):
    mocker.patch("phenoback.functions.analytics.process_observation")
    mocker.patch("phenoback.functions.analytics.process_remove_observation")
    mocker.patch("phenoback.functions.observation.updated_observation")
    mock = mocker.patch("phenoback.functions.activity.process_observation")
    mocker.patch("main.is_create_event", return_value=is_create)
    mocker.patch("main.is_field_updated", return_value=date_updated)
    mocker.patch("main.is_delete_event", return_value=is_delete)
    mocker.patch("main.get_field", return_value=phenophase)

    main.process_observation_write_activity("ignored", default_context)
    assert mock.called == expected


@pytest.mark.parametrize(
    "update_called, data, comment",
    [
        (False, {"oldValue": {}, "value": {}}, "invalid case"),
        (
            False,
            {
                "updateMask": {"fieldPaths": ["modified"]},
                "oldValue": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
                "value": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
            },
            "update modified",
        ),
        (
            True,
            {
                "updateMask": {"fieldPaths": ["other"]},
                "oldValue": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
                "value": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
            },
            "update sth else",
        ),
        (
            False,
            {
                "oldValue": {},
                "value": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
            },
            "create case",
        ),
        (
            False,
            {
                "oldValue": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
                "value": {},
            },
            "delete case",
        ),
    ],
)
def test_document_ts_update(mocker, update_called, data, comment):
    update_modified_document = mocker.patch(
        "phenoback.functions.documents.update_modified_document"
    )
    mocker.patch("phenoback.functions.documents.update_created_document")
    main.process_document_ts_write(data, mocker.MagicMock())
    assert update_modified_document.called == update_called, comment


def test_rollover(mocker):
    rollover_mock = mocker.patch("phenoback.functions.rollover.rollover")
    export_mock = mocker.patch("phenoback.functions.meteoswiss_export.process")
    main.rollover_manual("ignored", default_context)
    rollover_mock.assert_called_once()
    export_mock.assert_called_once()


@pytest.mark.parametrize("data, expected", [({"year": 2020}, 2020), ({}, None)])
def test_meteoswiss_export(mocker, data, expected):
    export_mock = mocker.patch("phenoback.functions.meteoswiss_export.process")
    main.export_meteoswiss_data_manual(data, default_context)
    export_mock.assert_called_once_with(expected)


def test_e2e_clear_user_individuals_http(mocker):
    e2e_mock = mocker.patch("phenoback.functions.e2e.delete_user_individuals")
    main.e2e_clear_user_individuals_http("ignored")
    e2e_mock.assert_called_once()
    e2e_mock.assert_called_with("q7lgBm5nm7PUkof20UdZ9D4d0CV2")


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "updateMask": {},
                "oldValue": {},
                "value": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                    }
                },
            },
            True,
        ),
        (
            {
                "updateMask": {"fieldPaths": ["resend"]},
                "oldValue": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                    }
                },
                "value": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                        "resend": {"numberValue": 1},
                    }
                },
            },
            True,
        ),
        (
            {
                "updateMask": {"fieldPaths": ["resend"]},
                "oldValue": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                        "resend": {"numberValue": 1},
                    }
                },
                "value": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                    }
                },
            },
            False,
        ),
        (
            {
                "updateMask": {},
                "oldValue": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                    }
                },
                "value": {},
            },
            False,
        ),
    ],
)
def test_process_invite_sending(mocker, data, expected):
    invite_mock = mocker.patch("phenoback.functions.invite.invite.process")
    main.process_invite_write(data, default_context)
    assert invite_mock.called == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "updateMask": {"fieldPaths": ["resend"]},
                "oldValue": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                        "sent": {"timestampValue": str(datetime(2021, 1, 1))},
                    }
                },
                "value": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                        "sent": {"timestampValue": str(datetime(2021, 1, 1))},
                        "resend": {"numberValue": 1},
                    }
                },
            },
            datetime(2021, 1, 1),
        ),
        (
            {
                "updateMask": {"fieldPaths": ["resend"]},
                "oldValue": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                    }
                },
                "value": {
                    "fields": {
                        "email": {"stringValue": "email@example.com"},
                        "user": {"stringValue": "user_id"},
                        "locale": {"stringValue": "locale"},
                        "resend": {"numberValue": 1},
                    }
                },
            },
            None,
        ),
    ],
)
def test_process_invite_sent(mocker, data, expected):
    invite_mock = mocker.patch("phenoback.functions.invite.invite.process")
    main.process_invite_write(data, default_context)
    invite_mock.assert_called()
    assert invite_mock.call_args[0][4] == expected


@pytest.mark.skip(reason="todo: refactor context and data handling -> helpers")
def test_process_user_write_update_invite():
    pass


def test_promote_ranger_http(mocker):
    email = "test@example.com"
    promote_mock = mocker.patch("phenoback.functions.phenorangers.promote")
    request_mock = mocker.patch.object(flask, "request")
    request_mock.headers = {"content-type": "application/json"}
    request_mock.get_json.return_value = {"email": email}
    main.promote_ranger_http(request_mock)
    promote_mock.assert_called_with(email)


def test_promote_ranger__content_type(mocker):
    request_mock = mocker.patch.object(flask, "request")
    request_mock.headers = {"content-type": "something"}
    assert main.promote_ranger_http(request_mock).status_code == 415


def test_promote_ranger__email_missing(mocker):
    request_mock = mocker.patch.object(flask, "request")
    request_mock.headers = {"content-type": "application/json"}
    request_mock.get_json.return_value = {"something": "something"}
    assert main.promote_ranger_http(request_mock).status_code == 400
