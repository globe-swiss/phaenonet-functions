import logging

import google.cloud.logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.cloud.logging_v2.resource import Resource

from phenoback.utils import gcloud


def init(log_id="Unknown"):  # pragma: no cover
    resource = Resource(
        type="cloud_function",
        labels={
            "function_name": gcloud.get_function_name(),
            "project_id": gcloud.get_project(),
            "region": gcloud.get_function_region(),
        },
    )

    client = google.cloud.logging.Client()
    logging.getLogger().handlers = []
    handler = CloudLoggingHandler(
        client, resource=resource, labels={"log_id": str(log_id)}
    )
    logging.getLogger().addHandler(handler)
