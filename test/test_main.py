# pylint: disable=too-many-arguments, wrong-import-position
from collections import namedtuple

import pytest

import main  # mocked via fixture

Context = namedtuple("context", "event_id, resource")  # todo: remove
default_context = Context(
    event_id="ignored", resource="document_path/document_id"
)  # todo: remove


@pytest.mark.parametrize(
    "entrypoint, functions",
    [
        (
            main.ps_import_meteoswiss_data,
            ["phenoback.functions.meteoswiss_import.main"],
        ),
        (
            main.ps_rollover_phenoyear,
            [
                "phenoback.functions.meteoswiss_export.main",
                "phenoback.functions.rollover.main",
            ],
        ),
        (
            main.ps_export_meteoswiss_data,
            ["phenoback.functions.meteoswiss_export.main"],
        ),
        (
            main.ps_iot_dragino_app,
            ["phenoback.functions.iot.app.main"],
        ),
        (
            main.ps_iot_dragino_bq,
            ["phenoback.functions.iot.bq.main"],
        ),
        (
            main.ps_iot_dragino_permarobotics,
            ["phenoback.functions.iot.permarobotics.main"],
        ),
    ],
)
def test_executes__pubsub(mocker, entrypoint, functions, pubsub_event, context):
    mocks = []
    for function in functions:
        mocks.append(mocker.patch(function))

    entrypoint(pubsub_event, context)

    for mock in mocks:
        mock.assert_called_once_with(pubsub_event, context)


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
        (main.fs_document_write, ["phenoback.functions.documents.main"]),
        (
            main.fs_invites_write,
            ["phenoback.functions.invite.invite.main"],
        ),
        (
            main.fs_individuals_write,
            ["phenoback.functions.map.main_enqueue"],
        ),
        (
            main.fs_observations_write,
            [
                "phenoback.functions.activity.main",
                "phenoback.functions.analytics.main",
                "phenoback.functions.individual.main",
            ],
        ),
    ],
)
def test_executes__firestore(mocker, entrypoint, functions, data, context):
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
        (
            main.http_reset_e2e_data,
            [
                "phenoback.functions.e2e.main",
            ],
        ),
        (
            main.http_promote_ranger,
            [
                "phenoback.functions.phenorangers.main",
            ],
        ),
        (
            main.http_iot_dragino,
            [
                "phenoback.functions.iot.dragino.main",
            ],
        ),
        (
            main.http_set_sensor,
            [
                "phenoback.functions.iot.app.main_set_sensor",
            ],
        ),
    ],
)
def test_executes__http(mocker, entrypoint, functions):
    request = object
    mock_return_value = "gcf return value"
    mocks = []
    for function in functions:
        mocks.append(mocker.patch(function, return_value=mock_return_value))

    result = entrypoint(request)

    for mock in mocks:
        mock.assert_called_once_with(request)
        assert result == mock_return_value


@pytest.mark.parametrize(
    "entrypoint, functions",
    [
        (
            main.st_appspot_finalize,
            [
                "phenoback.functions.thumbnails.main",
                "phenoback.functions.wld_import.main",
            ],
        ),
    ],
)
def test_executes__storage(mocker, entrypoint, functions, data, context):
    mocks = []
    for function in functions:
        mocks.append(mocker.patch(function))

    entrypoint(data, context)

    for mock in mocks:
        mock.assert_called_once_with(data, context)
