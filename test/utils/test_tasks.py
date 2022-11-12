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
def gcf_env(mocker) -> None:
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=PROJECT)
    mocker.patch("phenoback.utils.gcloud.get_location", return_value=LOCATION)


@pytest.fixture
def gcf_client(mocker, gcf_env) -> tasks.GCFClient:
    client_mock = mocker.patch.object(
        google.cloud.tasks_v2, "CloudTasksClient", autospec=True
    )
    client_mock.queue_path.return_value = PARENT
    mocker.patch("google.cloud.tasks_v2.CloudTasksClient", return_value=client_mock)
    return tasks.GCFClient(QUEUE, TARGET_FUNCTION)


class GCFClient:
    def test_init(self, gcf_client):
        client_mock = gcf_client.client

        assert gcf_client.queue == QUEUE
        assert gcf_client.target_function == TARGET_FUNCTION
        assert gcf_client.project == PROJECT
        assert gcf_client.location == LOCATION
        assert gcf_client.parent == PARENT
        client_mock.queue_path.assert_called_with(PROJECT, LOCATION, QUEUE)
        assert (
            gcf_client.url
            == f"https://{LOCATION}-{PROJECT}.cloudfunctions.net/{TARGET_FUNCTION}"
        )

    def test_send__headers(self, gcf_client):
        gcf_client.send("foo")
        GCFClient.check_default_headers(gcf_client)

    def test_send__text(self, gcf_client):
        payload = "foo"
        gcf_client.send(payload)
        GCFClient.check_default_headers(gcf_client)
        http_req_arg = GCFClient.get_request_args(gcf_client)["task"]["http_request"]

        assert http_req_arg["body"] == payload.encode()
        assert http_req_arg.get("headers") is None

    def test_send__json(self, gcf_client):
        payload = {"foo": "bar"}
        gcf_client.send(payload)
        GCFClient.check_default_headers(gcf_client)
        http_req_arg = GCFClient.get_request_args(gcf_client)["task"]["http_request"]

        assert http_req_arg["body"] == b'{"foo": "bar"}'
        assert http_req_arg.get("headers") == {"Content-type": "application/json"}

    def test_send__named(self, gcf_client):
        task_path = "task_path"
        task_name = "bar"
        gcf_client.client.task_path.return_value = task_path

        gcf_client.send("foo", task_name=task_name)
        GCFClient.check_default_headers(gcf_client)
        task_req_arg = GCFClient.get_request_args(gcf_client)["task"]

        assert task_req_arg["name"] == task_path
        gcf_client.client.task_path.assert_called_with(
            gcf_client.project, gcf_client.location, gcf_client.queue, task_name
        )

    def test_send__in_seconds(self, gcf_client):
        in_seconds = 360
        gcf_client.send("foo", in_seconds=in_seconds)
        GCFClient.check_default_headers(gcf_client)
        task_req_arg = GCFClient.get_request_args(gcf_client)["task"]

        assert task_req_arg["schedule_time"]

    def test_send__deadline(self, gcf_client):
        deadline = 360
        gcf_client.send("foo", deadline=deadline)
        GCFClient.check_default_headers(gcf_client)
        task_req_arg = GCFClient.get_request_args(gcf_client)["task"]

        assert task_req_arg["dispatch_deadline"]

    @staticmethod
    def check_default_headers(gcf_client) -> None:
        request_args = GCFClient.get_request_args(gcf_client)
        print(request_args["task"])
        assert request_args.get("parent") == gcf_client.parent
        assert request_args.get("task")
        assert request_args["task"]
        assert request_args["task"].get("http_request")
        assert (
            request_args["task"]["http_request"].get("http_method")
            == google.cloud.tasks_v2.HttpMethod.POST
        )
        assert request_args["task"]["http_request"].get("url") == gcf_client.url
        assert request_args["task"]["http_request"].get("oidc_token")
        assert (
            request_args["task"]["http_request"]["oidc_token"].get(
                "service_account_email"
            )
            == f"gcf-invoker@{gcf_client.project}.iam.gserviceaccount.com"
        )
        assert request_args["task"]["http_request"].get("body")

    @staticmethod
    def get_request_args(gcf_client) -> dict:
        return gcf_client.client.create_task.call_args[1]["request"]
