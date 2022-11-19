# pylint: disable=unused-argument,protected-access
from datetime import datetime

import google.cloud.tasks_v2
import pytest

from phenoback.utils import tasks

QUEUE = "queue"
PARENT = "parent"
URL = "https://example.com"


@pytest.fixture
def http_client(mocker) -> tasks.HTTPClient:
    client_mock = mocker.patch.object(
        google.cloud.tasks_v2, "CloudTasksClient", autospec=True
    )
    client_mock.queue_path.return_value = PARENT
    mocker.patch("google.cloud.tasks_v2.CloudTasksClient", return_value=client_mock)
    return tasks.HTTPClient(QUEUE, URL)


def test_init(http_client: tasks.HTTPClient, gcp_project, gcp_location):
    client_mock = http_client.client

    assert http_client.queue == QUEUE
    assert http_client.project == gcp_project
    assert http_client.location == gcp_location
    assert http_client.parent == PARENT
    client_mock.queue_path.assert_called_with(gcp_project, gcp_location, QUEUE)
    assert http_client.url == URL


def test_send__headers(http_client: tasks.HTTPClient):
    http_client.send("foo")
    check_default_headers(http_client)


def test_send__text(http_client: tasks.HTTPClient):
    payload = "foo"
    http_client.send(payload)
    check_default_headers(http_client)
    http_req_arg = get_request_args(http_client)["task"]["http_request"]

    assert http_req_arg["url"] == http_client.url
    assert http_req_arg["body"] == payload.encode()
    assert http_req_arg.get("headers") is None


def test_send__json(http_client: tasks.HTTPClient):
    payload = {"foo": "bar"}
    http_client.send(payload)
    check_default_headers(http_client)
    http_req_arg = get_request_args(http_client)["task"]["http_request"]

    assert http_req_arg["url"] == http_client.url
    assert http_req_arg["body"] == b'{"foo": "bar"}'
    assert http_req_arg.get("headers") == {"Content-type": "application/json"}


def test_send__named(http_client: tasks.HTTPClient):
    task_path = "task_path"
    task_name = "bar"
    http_client.client.task_path.return_value = task_path

    http_client.send("foo", task_name=task_name)
    check_default_headers(http_client)
    task_req_arg = get_request_args(http_client)["task"]

    assert task_req_arg["name"] == task_path
    http_client.client.task_path.assert_called_with(
        http_client.project, http_client.location, http_client.queue, task_name
    )


def test_send__at(http_client: tasks.HTTPClient):
    http_client.send("foo", at=datetime.now())
    check_default_headers(http_client)
    task_req_arg = get_request_args(http_client)["task"]

    assert task_req_arg["schedule_time"]


def test_send__deadline(http_client: tasks.HTTPClient):
    deadline = 360
    http_client.send("foo", deadline=deadline)
    check_default_headers(http_client)
    task_req_arg = get_request_args(http_client)["task"]

    assert task_req_arg["dispatch_deadline"]


def test_send__params(http_client: tasks.HTTPClient):
    http_client.send("foo", params={"foo": "bar"})
    check_default_headers(http_client)
    task_req_arg = get_request_args(http_client)["task"]

    assert task_req_arg["http_request"]["url"] == f"{http_client.url}?foo=bar"


@pytest.mark.parametrize(
    "params, expected", [({"p1": "v1", "p2": "v2"}, "?p1=v1&p2=v2"), (None, "")]
)
def test_encode_params(http_client, params, expected):
    assert http_client.encode_params(params) == expected


def check_default_headers(http_client) -> None:
    request_args = get_request_args(http_client)
    print(request_args["task"])
    assert request_args.get("parent") == http_client.parent
    assert request_args.get("task")
    assert request_args["task"]
    assert request_args["task"].get("http_request")
    assert (
        request_args["task"]["http_request"].get("http_method")
        == google.cloud.tasks_v2.HttpMethod.POST
    )
    assert request_args["task"]["http_request"].get("url").startswith(http_client.url)
    assert request_args["task"]["http_request"].get("oidc_token")
    assert (
        request_args["task"]["http_request"]["oidc_token"].get("service_account_email")
        == f"gcf-invoker@{http_client.project}.iam.gserviceaccount.com"
    )
    assert request_args["task"]["http_request"].get("body")


def get_request_args(http_client) -> dict:
    return http_client.client.create_task.call_args[1]["request"]
