# pylint: disable=too-many-arguments, wrong-import-position
from collections import namedtuple
from datetime import datetime, timezone
from unittest.mock import ANY, MagicMock

import firebase_admin
import pytest
import sentry_sdk
from flask import Request, Response
from werkzeug.test import EnvironBuilder

from phenoback.utils import glogging

firebase_admin.initialize_app = MagicMock()
glogging.init = MagicMock()
sentry_sdk.init = MagicMock()

import main

Context = namedtuple("context", "event_id, resource")
default_context = Context(
    event_id="ignored", resource="document_path/document_id"
)  # todo: move to fixture


@pytest.fixture()
def context():
    return default_context


@pytest.fixture()
def data():
    return {"foo": "bar"}


@pytest.mark.parametrize(
    "entrypoint, functions",
    [
        (
            main.fs_users_write,
            [
                "phenoback.functions.users.main",
                "phenoback.functions.invite.register.main",
            ],
        ),
        (
            main.ps_import_meteoswiss_data_publish,
            ["phenoback.functions.meteoswiss_import.main"],
        ),
    ],
)
def test_executes(mocker, entrypoint, functions, data, context):
    mocks = []
    for function in functions:
        mocks.append(mocker.patch(function))

    entrypoint(data, context)

    for mock in mocks:
        mock.assert_called_once_with(data, context)


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
        "phenoback.functions.observation.updated_observation"
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
    "called, data",
    [
        (
            "updated",
            {
                "updateMask": {"fieldPaths": ["modified"]},
                "oldValue": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
                "value": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
            },
        ),
        (
            "created",
            {
                "updateMask": {},
                "oldValue": {},
                "value": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
            },
        ),
        (
            "deleted",
            {
                "updateMask": {"fieldPaths": ["modified"]},
                "oldValue": {
                    "fields": {"modified": {"timestampValue": str(datetime.now())}}
                },
                "value": {},
            },
        ),
    ],
)
def test_document_ts_update(mocker, called, data):
    update_modified_document_mock = mocker.patch(
        "phenoback.functions.documents.update_modified_document"
    )
    update_created_document_mock = mocker.patch(
        "phenoback.functions.documents.update_created_document"
    )
    main.process_document_ts_write(data, mocker.MagicMock())
    assert update_modified_document_mock.called == (called == "updated")
    assert update_created_document_mock.called == (called == "created")
    # nothing to do for delete


def test_document_ts_update__overwrite_created(mocker):
    create_ts = datetime.utcnow().replace(tzinfo=timezone.utc)
    data = {
        "updateMask": {"fieldPaths": ["created", "somevalue"]},
        "oldValue": {"fields": {"created": {"timestampValue": str(create_ts)}}},
        "value": {"fields": {"somevalue": {"something"}}},
    }
    update_modified_document_mock = mocker.patch(
        "phenoback.functions.documents.update_modified_document"
    )

    main.process_document_ts_write(data, mocker.MagicMock())
    update_modified_document_mock.assert_called_once_with(
        ANY, ANY, data["updateMask"]["fieldPaths"], create_ts
    )


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
    assert isinstance(main.e2e_clear_user_individuals_http("ignored"), Response)
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


def test_promote_ranger_http(mocker):
    email = "test@example.com"
    promote_mock = mocker.patch("phenoback.functions.phenorangers.promote")
    request = Request(
        EnvironBuilder(
            method="POST",
            json={"email": email},
        ).get_environ()
    )
    main.promote_ranger_http(request)
    promote_mock.assert_called_with(email)


def test_promote_ranger__content_type():
    request = Request(
        EnvironBuilder(
            method="POST", headers={"content-type": "something"}
        ).get_environ()
    )
    assert main.promote_ranger_http(request).status_code == 415


def test_promote_ranger__email_missing():
    request = Request(
        EnvironBuilder(
            method="POST",
            json={"something": "something"},
        ).get_environ()
    )
    assert main.promote_ranger_http(request).status_code == 400


@pytest.mark.parametrize(
    "main_function, call_function_name, pathfile, called",
    [
        (
            main.create_thumbnail_finalize,
            "thumbnails.process_new_image",
            "images/anything_in_this_folder",
            True,
        ),
        (
            main.create_thumbnail_finalize,
            "thumbnails.process_new_image",
            "other_folder/anything_in_this_folder",
            False,
        ),
        (
            main.import_wld_data_finalize,
            "wld_import.import_data",
            "private/wld_import/anything_in_this_folder",
            True,
        ),
        (
            main.import_wld_data_finalize,
            "wld_import.import_data",
            "private/other_folder/anything_in_this_folder",
            False,
        ),
    ],
)
def test_storage_triggers(mocker, main_function, call_function_name, pathfile, called):
    """
    Test all functions based on storage triggers to correctly limit
    the function invocation to specific folders.
    """
    mock = mocker.patch(f"phenoback.functions.{call_function_name}")
    main_function({"name": pathfile}, default_context)
    assert mock.called == called


def test_process_dragino_http(mocker):
    process_mock = mocker.patch("phenoback.functions.iot.dragino.process_dragino")
    payload = {"foo": "bar"}
    request = Request(
        EnvironBuilder(
            method="POST",
            json=payload,
        ).get_environ()
    )
    result = main.process_dragino_http(request)

    assert result.status_code == 200
    process_mock.assert_called_with(payload)


def test_process_dragino_phaenonet(mocker):
    encoded_data = b"eyJmb28iOiJiYXIifQ=="
    process_mock = mocker.patch("phenoback.functions.iot.app.process_dragino")

    main.process_dragino_phaenonet({"data": encoded_data}, None)

    process_mock.assert_called_with({"foo": "bar"})


def test_process_dragino_bq(mocker):
    encoded_data = b"eyJmb28iOiJiYXIifQ=="
    process_mock = mocker.patch("phenoback.utils.bq.insert_data")

    main.process_dragino_bq({"data": encoded_data}, None)

    process_mock.assert_called_with("iot.raw", {"foo": "bar"})


def test_set_sensor_http__ok(mocker):
    set_sensor_mock = mocker.patch(
        "phenoback.functions.iot.app.set_sensor", return_value=True
    )
    payload = {"individual": "foo", "deveui": "bar", "year": 2000}
    request = Request(
        EnvironBuilder(
            method="POST",
            json=payload,
        ).get_environ()
    )

    result = main.set_sensor_http(request)

    assert result.status_code == 200
    set_sensor_mock.assert_called_with("foo", 2000, "bar")


@pytest.mark.parametrize(
    "payload, status",
    [
        ({"individual": "foo"}, 400),
        ({"deveui": "bar"}, 400),
        (
            {
                "individual": "foo",
                "deveui": "bar",
            },
            400,
        ),
        (
            {"individual": "foo", "deveui": "bar", "year": 2000},
            404,
        ),
    ],
)
def test_set_sensor_http__error(mocker, payload, status):
    mocker.patch("phenoback.functions.iot.app.set_sensor", return_value=False)
    request = Request(
        EnvironBuilder(
            method="POST",
            json=payload,
        ).get_environ()
    )

    result = main.set_sensor_http(request)

    assert result.status_code == status
