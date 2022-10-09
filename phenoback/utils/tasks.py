import datetime
import json
import logging
from typing import Dict, Union

import google.cloud.tasks_v2.types.task
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from phenoback.utils import gcloud

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class HTTPClient:
    def __init__(self, queue: str, target_function: str) -> None:
        self.queue = queue
        self.target_function = target_function
        self.project = gcloud.get_project()
        # assume task queue and functions is default location
        self.location = gcloud.get_location()
        self.client = tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(self.project, self.location, self.queue)
        self.url = f"https://{self.location}-{self.project}.cloudfunctions.net/{self.target_function}"
        log.debug(
            "Client created on sending to %s dispatching to %s", queue, target_function
        )

    def send(
        self,
        payload: Union[Dict, str],
        task_name: str = None,
        in_seconds: int = None,
        deadline: int = None,
    ) -> google.cloud.tasks_v2.types.task.Task:
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": self.url,
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

        if in_seconds is not None:
            # Convert "seconds from now" into an rfc3339 datetime string.
            target_date = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=in_seconds
            )
            # pylint: disable=no-member
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(target_date)
            task["schedule_time"] = timestamp

        if task_name is not None:
            task["name"] = self.client.task_path(
                self.project, self.location, self.queue, task_name
            )

        if deadline is not None:
            # pylint: disable=no-member
            duration = duration_pb2.Duration()
            duration.FromSeconds(deadline)
            task["dispatch_deadline"] = duration

        response = self.client.create_task(
            request={"parent": self.parent, "task": task}
        )

        log.debug("Created task on %s (%s)", self.queue, response.name)
        return response
