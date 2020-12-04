import logging
import os

import google.cloud.logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.cloud.logging_v2.resource import Resource


def init(log_id="Unknown"):  # pragma: no cover
    resource = Resource(
        type="cloud_function",
        labels={
            "function_name": os.getenv("FUNCTION_NAME", "Unknown"),
            "project_id": os.getenv("GCP_PROJECT", "Unknown"),
            "region": os.getenv("FUNCTION_REGION", "Unknown"),
        },
    )

    client = google.cloud.logging.Client()
    logging.getLogger().handlers = []
    handler = CloudLoggingHandler(
        client, resource=resource, labels={"log_id": str(log_id)}
    )
    logging.getLogger().addHandler(handler)
