import logging
from functools import lru_cache
from typing import List, Union

from google.cloud import bigquery

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@lru_cache
def client():
    return bigquery.Client()


def insert_data(table: str, data: Union[dict, List[dict]]):
    if isinstance(data, dict):
        data = [data]
    log.debug("Insert %i rows into %s", len(data), table)
    errors = client().insert_rows_json(table, data)
    if errors:
        log.error("errors: %s", errors)
