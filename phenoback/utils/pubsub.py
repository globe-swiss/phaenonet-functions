import json
import logging
from typing import Dict, Union

from google.cloud import pubsub_v1

from phenoback.utils import gcloud

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Publisher:
    def __init__(self, topic: str) -> None:
        self.client = pubsub_v1.PublisherClient()
        self.topic = topic
        self.project = gcloud.get_project()
        self.topic_path = self.client.topic_path(self.project, self.topic)
        log.debug("Publisher created for topic %s", self.topic)

    def send(
        self, payload: Union[Dict, str], metadata: Dict[str, Union[bytes, str]] = None
    ) -> None:
        if metadata is None:
            metadata = {}
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        bytes_payload = payload.encode("utf-8")

        msg_id = self.client.publish(
            self.topic_path, bytes_payload, **metadata
        ).result()

        log.debug("Published message on topic %s (%s)", self.topic, msg_id)
