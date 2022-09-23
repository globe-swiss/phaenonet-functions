import logging
from datetime import datetime
from typing import List

from phenoback.utils import firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

MODIFIED_KEY = "modified"
CREATED_KEY = "created"


def update_created_document(collection: str, document_id: str):
    log.info("create event: update created, modified on %s.%s", collection, document_id)
    f.update_document(
        collection,
        document_id,
        {CREATED_KEY: f.SERVER_TIMESTAMP, MODIFIED_KEY: f.SERVER_TIMESTAMP},
    )


def update_modified_document(
    collection: str,
    document_id: str,
    updated_fields: List[str],
    created: datetime = None,
):
    log.debug(
        "update event: %s.%s, fields: %s, created: %s",
        collection,
        document_id,
        updated_fields,
        created,
    )
    if _should_update_modified(updated_fields):
        if created:
            f.update_document(
                collection,
                document_id,
                {CREATED_KEY: created, MODIFIED_KEY: f.SERVER_TIMESTAMP},
            )
            log.info(
                "update event: update modified and create=%s on %s.%s ",
                created,
                collection,
                document_id,
            )
        else:
            f.update_document(
                collection, document_id, {MODIFIED_KEY: f.SERVER_TIMESTAMP}
            )
            log.info("update event: update modified on %s.%s", collection, document_id)
    else:
        log.debug("update event: nothing to do: fields=%s", updated_fields)


def _should_update_modified(updated_fields: List[str]):
    return not (
        all(field in [CREATED_KEY, MODIFIED_KEY] for field in updated_fields)
        or any(field.startswith("sensor.") for field in updated_fields)
    )
