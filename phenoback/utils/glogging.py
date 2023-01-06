import logging

import google.cloud.logging


def init():  # pragma: no cover
    client = google.cloud.logging.Client()
    client.setup_logging()
    logging.getLogger().setLevel(logging.WARNING)
