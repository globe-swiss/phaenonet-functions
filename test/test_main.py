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

Context = namedtuple("context", "event_id, resource")  # todo: remove
default_context = Context(
    event_id="ignored", resource="document_path/document_id"
)  # todo: remove


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
        (main.fs_document_write, ["phenoback.functions.documents.main"]),
        (
            main.st_appspot_finalize,
            [
                "phenoback.functions.thumbnails.main",
                "phenoback.functions.wld_import.main",
            ],
        ),
        (
            main.ps_rollover_phenoyear_publish,
            [
                "phenoback.functions.meteoswiss_export.main",
                "phenoback.functions.rollover.main",
            ],
        ),
        (
            main.ps_export_meteoswiss_data_publish,
            ["phenoback.functions.meteoswiss_export.main"],
        ),
        (
            main.fs_invites_write,
            ["phenoback.functions.invite.invite.main"],
        ),
        (
            main.fs_individuals_write,
            ["phenoback.functions.map.main_enqueue"],
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
    "entrypoint, functions",
    [
        (
            main.http_individuals_write,
            [
                "phenoback.functions.map.main_process",
            ],
        ),
    ],
)
def test_executes__http(mocker, entrypoint, functions):
    request = object
    mock_return_value = "value"
    mocks = []
    for function in functions:
        mocks.append(mocker.patch(function, return_value=mock_return_value))

    result = entrypoint(request)

    for mock in mocks:
        mock.assert_called_once_with(request)
        assert result == mock_return_value


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


def test_e2e_clear_user_individuals_http(mocker):
    e2e_mock = mocker.patch("phenoback.functions.e2e.delete_user_individuals")
    assert isinstance(main.e2e_clear_user_individuals_http("ignored"), Response)
    e2e_mock.assert_called_once()
    e2e_mock.assert_called_with("q7lgBm5nm7PUkof20UdZ9D4d0CV2")


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
