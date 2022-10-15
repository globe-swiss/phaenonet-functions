# pylint: disable=unused-argument,protected-access
import google.cloud.tasks_v2
import pytest

from phenoback.utils import tasks

PROJECT = "project"
LOCATION = "location"
QUEUE = "queue"
TARGET_FUNCTION = "function"
PARENT = "parent"


@pytest.fixture
def fkn_env(mocker) -> None:
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=PROJECT)
    mocker.patch("phenoback.utils.gcloud.get_location", return_value=LOCATION)


@pytest.fixture
def http_client(mocker, fkn_env) -> tasks.HTTPClient:
    client_mock = mocker.patch.object(
        google.cloud.tasks_v2, "CloudTasksClient", autospec=True
    )
    client_mock.queue_path.return_value = PARENT
    mocker.patch("google.cloud.tasks_v2.CloudTasksClient", return_value=client_mock)
    return tasks.HTTPClient(QUEUE, TARGET_FUNCTION)


class TestHttpClient:
    def test_init(self, http_client):
        client_mock = http_client.client

        assert http_client.queue == QUEUE
        assert http_client.target_function == TARGET_FUNCTION
        assert http_client.project == PROJECT
        assert http_client.location == LOCATION
        assert http_client.parent == PARENT
        client_mock.queue_path.assert_called_with(PROJECT, LOCATION, QUEUE)
        assert (
            http_client.url
            == f"https://{LOCATION}-{PROJECT}.cloudfunctions.net/{TARGET_FUNCTION}"
        )

    def test_send__headers(self, http_client):
        http_client.send("foo")
        TestHttpClient.check_default_headers(http_client)

    def test_send__text(self, http_client):
        payload = "foo"
        http_client.send(payload)
        TestHttpClient.check_default_headers(http_client)
        http_req_arg = TestHttpClient.get_request_args(http_client)["task"][
            "http_request"
        ]

        assert http_req_arg["body"] == payload.encode()
        assert http_req_arg.get("headers") is None

    def test_send__json(self, http_client):
        payload = {"foo": "bar"}
        http_client.send(payload)
        TestHttpClient.check_default_headers(http_client)
        http_req_arg = TestHttpClient.get_request_args(http_client)["task"][
            "http_request"
        ]

        assert http_req_arg["body"] == b'{"foo": "bar"}'
        assert http_req_arg.get("headers") == {"Content-type": "application/json"}

    def test_send__named(self, http_client):
        task_path = "task_path"
        task_name = "bar"
        http_client.client.task_path.return_value = task_path

        http_client.send("foo", task_name=task_name)
        TestHttpClient.check_default_headers(http_client)
        task_req_arg = TestHttpClient.get_request_args(http_client)["task"]

        assert task_req_arg["name"] == task_path
        http_client.client.task_path.assert_called_with(
            http_client.project, http_client.location, http_client.queue, task_name
        )

    def test_send__in_seconds(self, http_client):
        in_seconds = 360
        http_client.send("foo", in_seconds=in_seconds)
        TestHttpClient.check_default_headers(http_client)
        task_req_arg = TestHttpClient.get_request_args(http_client)["task"]

        assert task_req_arg["schedule_time"]

    def test_send__deadline(self, http_client):
        deadline = 360
        http_client.send("foo", deadline=deadline)
        TestHttpClient.check_default_headers(http_client)
        task_req_arg = TestHttpClient.get_request_args(http_client)["task"]

        assert task_req_arg["dispatch_deadline"]

    @staticmethod
    def check_default_headers(http_client) -> None:
        request_args = TestHttpClient.get_request_args(http_client)
        print(request_args["task"])
        assert request_args.get("parent") == http_client.parent
        assert request_args.get("task")
        assert request_args["task"]
        assert request_args["task"].get("http_request")
        assert (
            request_args["task"]["http_request"].get("http_method")
            == google.cloud.tasks_v2.HttpMethod.POST
        )
        assert request_args["task"]["http_request"].get("url") == http_client.url
        assert request_args["task"]["http_request"].get("oidc_token")
        assert (
            request_args["task"]["http_request"]["oidc_token"].get(
                "service_account_email"
            )
            == f"gcf-invoker@{http_client.project}.iam.gserviceaccount.com"
        )
        assert request_args["task"]["http_request"].get("body")

    @staticmethod
    def get_request_args(http_client) -> dict:
        return http_client.client.create_task.call_args[1]["request"]
