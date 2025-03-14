# pylint: disable=wrong-import-position, too-many-positional-arguments
from unittest.mock import ANY

import pytest

import main  # mocked via fixture


def test_invoke__exception(data, context):
    def function():
        with main.setup(data, context):
            value = False
            with main.invoke():
                raise KeyError("Some error")
            with main.invoke():
                value = True
            return value

    assert function()


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
            main.ps_iot_dragino,
            [
                "phenoback.functions.iot.app.main",
                "phenoback.functions.iot.bq.main",
                # "phenoback.functions.iot.permarobotics.main", -> not called: only for productive environment
            ],
        ),
        (
            main.ps_process_statistics,
            [
                "phenoback.functions.statistics.weekly.main",
            ],
        ),
    ],
)
def test_executes__pubsub(
    mocker, entrypoint, functions, pubsub_event, pubsub_event_data, context
):
    mocks = []
    for function in functions:
        mocks.append(mocker.patch(function))

    entrypoint(pubsub_event, context)

    for mock in mocks:
        mock.assert_called_once_with(pubsub_event_data, context)


@pytest.mark.parametrize(
    "project",
    ["phaenonet", "phaenonet-test", None],
)
def test_executes__ps_iot_dragino__environments(mocker, project, pubsub_event, context):
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=project)
    mock_app_main = mocker.patch("phenoback.functions.iot.app.main")
    mock_bq_main = mocker.patch("phenoback.functions.iot.bq.main")
    mock_permarobotics_main = mocker.patch("phenoback.functions.iot.permarobotics.main")

    main.ps_iot_dragino(pubsub_event, context)

    assert mock_app_main.called
    assert mock_bq_main.called
    assert mock_permarobotics_main.called == (project == "phaenonet")


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
            [
                "phenoback.functions.map.main_enqueue",
                "phenoback.functions.iot.app.main_individual_updated",
            ],
        ),
        (
            main.fs_observations_write,
            [
                "phenoback.functions.activity.main",
                "phenoback.functions.analytics.main_enqueue",
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
            main.http_individuals_write__map,
            [
                "phenoback.functions.map.main_process",
            ],
        ),
        (
            main.http_observations_write__analytics,
            [
                "phenoback.functions.analytics.main_process",
            ],
        ),
        (
            main.http_reset_e2e_data,
            [
                "phenoback.functions.e2e.main_reset",
            ],
        ),
        (
            main.http_restore_e2e_users,
            [
                "phenoback.functions.e2e.main_restore",
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


@pytest.mark.parametrize(
    "project, result",
    [
        ("phaenonet", ("production", 1.0, ANY)),
        ("phaenonet-test", ("test", ANY, ANY)),
        (None, ("local", 0.0, 0.0)),
    ],
)
def test_sentry_environment(mocker, project, result):
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=project)
    assert main.sentry_environment() == result
