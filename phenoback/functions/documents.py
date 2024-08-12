import logging
from datetime import datetime

from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

MODIFIED_KEY = "modified"
CREATED_KEY = "created"


def main(data, context):
    """
    Updates create and modified timestamps on documents.
    """
    collection_path = g.get_collection_path(context)
    document_id = g.get_document_id(context)
    source = g.get_field(data, "source", expected=False) or g.get_field(
        data, "source", old_value=True, expected=False
    )

    if g.is_create_event(data):
        log.debug("document %s was created (%s)", context.resource, source)
        update_created_document(collection_path, document_id)
    elif g.is_update_event(data):
        log.debug("document %s was updated (%s)", context.resource, source)
        update_modified_document(
            collection_path,
            document_id,
            g.get_fields_updated(data),
            g.get_field(data, CREATED_KEY, old_value=True, expected=False),
        )
    elif g.is_delete_event(data):
        log.debug("document %s was deleted (%s)", context.resource, source)
    else:  # pragma: no cover
        log.error("Unexpected case for %s (%s)", context.resource, source)


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
    updated_fields: list[str],
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


def _should_update_modified(updated_fields: list[str]):
    return not (
        all(field in [CREATED_KEY, MODIFIED_KEY] for field in updated_fields)
        or any(field.startswith("sensor.") for field in updated_fields)
    )
