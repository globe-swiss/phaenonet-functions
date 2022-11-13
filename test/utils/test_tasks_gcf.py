# pylint: disable=unused-argument,protected-access
from datetime import datetime

import pytest

from phenoback.utils import tasks

PROJECT = "project"
LOCATION = "location"
QUEUE = "queue"
TARGET_FUNCTION = "function"
PARENT = "parent"


@pytest.fixture
def gcf_client(mocker) -> tasks.GCFClient:
    mocker.patch.object(tasks, "HTTPClient", autospec=True)
    return tasks.GCFClient(QUEUE, TARGET_FUNCTION)


def test_init(mocker, gcp_location, gcp_project):
    http_client_mock = mocker.patch.object(tasks, "HTTPClient", autospec=True)
    gcf_client = tasks.GCFClient(QUEUE, TARGET_FUNCTION)

    assert gcf_client.http_client

    assert gcf_client.target_project == gcp_project
    assert gcf_client.target_location == gcp_location
    assert gcf_client.target_function == TARGET_FUNCTION
    http_client_mock.assert_called_with(
        QUEUE,
        f"https://{gcf_client.target_location}-{gcf_client.target_project}.cloudfunctions.net/{gcf_client.target_function}",
    )


def test_init__target(mocker):
    http_client_mock = mocker.patch.object(tasks, "HTTPClient", autospec=True)
    gcf_client = tasks.GCFClient(
        QUEUE, TARGET_FUNCTION, target_project="foo", target_location="bar"
    )

    assert gcf_client.http_client

    assert gcf_client.target_project == "foo"
    assert gcf_client.target_location == "bar"
    assert gcf_client.target_function == TARGET_FUNCTION
    http_client_mock.assert_called_with(
        QUEUE,
        f"https://{gcf_client.target_location}-{gcf_client.target_project}.cloudfunctions.net/{gcf_client.target_function}",
    )


def test_send(gcf_client: tasks.GCFClient):
    payload = "foo"
    task_name = "name"
    at = datetime.now()
    deadline = 10

    gcf_client.send(payload, task_name=task_name, at=at, deadline=deadline)

    gcf_client.http_client.send.assert_called_with(
        payload=payload, task_name=task_name, at=at, deadline=deadline
    )
