import logging
from datetime import datetime
from typing import List

from phenoback.utils import firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

MODIFIED_KEY = "modified"
CREATED_KEY = "created"


def update_created_document(collection: str, document_id: str):
    log.info("create event update %s.%s", collection, document_id)
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
        "modified update event: %s.%s, fields: %s, created: %s",
        collection,
        document_id,
        updated_fields,
        created,
    )
    if set(updated_fields).difference([CREATED_KEY, MODIFIED_KEY]):
        if created:
            f.update_document(
                collection,
                document_id,
                {CREATED_KEY: created, MODIFIED_KEY: f.SERVER_TIMESTAMP},
            )
            log.info(
                "modified update event: %s.%s with create=%s",
                collection,
                document_id,
                created,
            )
        else:
            f.update_document(
                collection, document_id, {MODIFIED_KEY: f.SERVER_TIMESTAMP}
            )
            log.info("modified update event: %s.%s", collection, document_id)
