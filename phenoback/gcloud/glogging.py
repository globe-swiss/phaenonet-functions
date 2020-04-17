import os
from datetime import datetime
import logging
from google.cloud.logging import _helpers
from google.cloud.logging.handlers.transports.background_thread import _Worker
import google.cloud.logging
from google.cloud.logging.resource import Resource


log_id = None


def my_enqueue(self, record, message, resource=None, labels=None, trace=None, span_id=None):
    resource = Resource(type='cloud_function',
                        labels={'function_name': os.getenv('FUNCTION_NAME', 'Unknown'),
                                  'project_id': os.getenv('GCP_PROJECT', 'Unknown'),
                                  'region': os.getenv('FUNCTION_REGION', 'Unknown')
                                })
    if not labels:
        labels = {}
    labels.update({'log_id': log_id})
    queue_entry = {
        "info": {"message": message, "python_logger": record.name},
        "severity": _helpers._normalize_severity(record.levelno),
        "resource": resource,
        "labels": labels,
        "trace": trace,
        "span_id": span_id,
        "timestamp": datetime.utcfromtimestamp(record.created),
    }

    self._queue.put_nowait(queue_entry)


def init(log_identifier=None):
    global log_id
    log_id = log_identifier
    _Worker.enqueue = my_enqueue

    client = google.cloud.logging.Client()
    logging.getLogger().handlers = []
    handler = client.get_default_handler()
    logging.getLogger().addHandler(handler)

