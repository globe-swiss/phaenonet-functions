from datetime import datetime
from phenoback.utils.firestore import update_document

MODIFIED_KEY = "modified"
CREATED_KEY = "created"


def update_created_document(collection: str, document_id: str):  # pragma: no cover
    now = datetime.now()
    update_document(collection, document_id, {CREATED_KEY: now, MODIFIED_KEY: now})


def update_modified_document(collection: str, document_id: str):  # pragma: no cover
    update_document(collection, document_id, {MODIFIED_KEY: datetime.now()})
