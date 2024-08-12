import datetime
import json
import logging
import urllib.parse

import google.cloud.tasks_v2.types.task
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from phenoback.utils import gcloud

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class HTTPClient:
    def __init__(self, queue: str, url: str) -> None:
        self.queue = queue
        self.client = tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(self.project, self.location, self.queue)
        self.url = url
        log.debug("Client created on sending to %s dispatching to %s", queue, self.url)

    @property
    def project(self):
        return gcloud.get_project()

    @property
    def location(self):
        return gcloud.get_location()

    def send(
        self,
        payload: dict | str,
        params: dict = None,
        task_name: str = None,
        at: datetime.datetime = None,
        deadline: int = None,
    ) -> google.cloud.tasks_v2.types.task.Task:
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{self.url}{self.encode_params(params)}",
                "oidc_token": {
                    "service_account_email": f"gcf-invoker@{self.project}.iam.gserviceaccount.com",
                },
            }
        }

        if isinstance(payload, dict):
            payload = json.dumps(payload)
            task["http_request"]["headers"] = {"Content-type": "application/json"}

        converted_payload = payload.encode()
        task["http_request"]["body"] = converted_payload

        if at:
            # pylint: disable=no-member
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(at)
            task["schedule_time"] = timestamp

        if task_name:
            task["name"] = self.client.task_path(
                self.project, self.location, self.queue, task_name
            )

        if deadline:
            # pylint: disable=no-member
            duration = duration_pb2.Duration()
            duration.FromSeconds(deadline)
            task["dispatch_deadline"] = duration

        response = self.client.create_task(
            request={"parent": self.parent, "task": task}
        )

        log.debug("Created task on %s (%s)", self.queue, response.name)
        return response

    def encode_params(self, params: dict) -> str:
        return "?" + urllib.parse.urlencode(params) if params else ""


class GCFClient:
    def __init__(
        self,
        queue: str,
        target_function: str,
        target_project: str = None,
        target_location: str = None,
    ) -> None:
        log.debug(
            "Create client sending to %s dispatching to function %s",
            queue,
            target_function,
        )
        self.target_function = target_function
        # default to current project's values
        self.target_location = (
            target_location if target_location else gcloud.get_location()
        )
        self.target_project = target_project if target_project else gcloud.get_project()
        self.http_client = HTTPClient(
            queue,
            f"https://{self.target_location}-{self.target_project}.cloudfunctions.net/{self.target_function}",
        )

    def send(
        self,
        payload: dict | str,
        task_name: str = None,
        at: datetime.datetime = None,
        deadline: int = None,
    ) -> google.cloud.tasks_v2.types.task.Task:
        return self.http_client.send(
            payload=payload, task_name=task_name, at=at, deadline=deadline
        )
