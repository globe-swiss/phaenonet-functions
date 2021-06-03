import logging
from typing import Any, List, Optional

from firebase_admin import firestore
from google.cloud.firestore_v1 import DELETE_FIELD as _DELETE_FIELD
from google.cloud.firestore_v1 import SERVER_TIMESTAMP as _SERVER_TIMESTAMP
from google.cloud.firestore_v1 import ArrayUnion as _ArrayUnion
from google.cloud.firestore_v1 import Increment as _Increment
from google.cloud.firestore_v1 import Query as _Query
from google.cloud.firestore_v1.client import Client as _Client
from google.cloud.firestore_v1.collection import (
    CollectionReference as _CollectionReference,
)
from google.cloud.firestore_v1.transaction import Transaction as _Transaction
from google.cloud.firestore_v1 import transactional as _transactional

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_db = None  # pylint: disable=invalid-name

# exported
DELETE_FIELD = _DELETE_FIELD
SERVER_TIMESTAMP = _SERVER_TIMESTAMP
ArrayUnion = _ArrayUnion
Increment = _Increment
Query = _Query
Client = _Client
CollectionReference = _CollectionReference
Transaction = _Transaction
transactional = _transactional


def firestore_client() -> Client:
    global _db  # pylint: disable=invalid-name,global-statement
    if not _db:  # pragma: no cover
        _db = firestore.client()
    return _db


def get_transaction():
    return firestore_client().transaction()


def delete_document(
    collection: str, document_id: str, transaction: Transaction = None
) -> None:
    log.debug("Delete document %s from %s", document_id, collection)
    ref = firestore_client().collection(collection).document(document_id)
    if transaction:
        transaction.delete(ref)
    else:
        ref.delete()


def _delete_batch(coll_ref, batch_size: int = 1000):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        log.debug("Deleting doc %s => %s", doc.id, doc.to_dict())
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return _delete_batch(coll_ref, batch_size)
    else:
        return None


def delete_collection(collection: str, batch_size: int = 1000) -> None:
    _delete_batch(get_collection(collection), batch_size)


def delete_batch(
    collection: str, field_path: str, op_string: str, value: Any, batch_size: int = 1000
) -> None:
    query = query_collection(collection, field_path, op_string, value)
    _delete_batch(query, batch_size=batch_size)


def write_batch(
    collection: str,
    key: str,
    data: List[dict],
    merge: bool = False,
    batch_size: int = 500,
) -> None:
    log.info("Batch-write %i documents to %s", len(data), collection)
    batch = firestore_client().batch()
    cnt = 0
    for item in data:
        cnt += 1
        ref = firestore_client().collection(collection).document(str(item[key]))
        item.pop(key)
        batch.set(ref, item, merge=merge)
        if cnt == batch_size:
            log.debug("Commiting %i documents on %s", cnt, collection)
            batch.commit()
            cnt = 0
    log.debug("Committing %i documents on %s", cnt, collection)
    batch.commit()


def write_document(
    collection: str,
    document_id: Optional[str],
    data: dict,
    merge: bool = False,
    transaction: Transaction = None,
) -> None:
    log.debug(
        "Write document %s to %s (%s)",
        document_id,
        collection,
        transaction.id if transaction else None,
    )
    ref = firestore_client().collection(collection).document(document_id)
    if transaction:
        transaction.set(ref, data, merge=merge)
    else:
        ref.set(data, merge=merge)


def update_document(
    collection: str,
    document_id: str,
    data: dict,
    transaction: Transaction = None,
) -> None:
    log.debug(
        "Update document %s in %s (%s)",
        document_id,
        collection,
        transaction.id if transaction else None,
    )
    ref = firestore_client().collection(collection).document(document_id)
    if transaction:
        transaction.update(ref, data)
    else:
        ref.update(data)


def get_document(
    collection: str, document_id: str, transaction: Transaction = None
) -> Optional[dict]:
    log.debug(
        "Get document %s in %s (%s)",
        document_id,
        collection,
        transaction.id if transaction else None,
    )
    return (
        firestore_client()
        .collection(collection)
        .document(document_id)
        .get(transaction=transaction)
        .to_dict()
    )


def query_collection(
    collection: str, field_path: str, op_string: str, value: Any
) -> Query:
    log.debug("Query %s where %s %s %s", collection, field_path, op_string, value)
    return firestore_client().collection(collection).where(field_path, op_string, value)


def get_collection(collection: str) -> CollectionReference:
    log.debug("Query collection %s", collection)
    return firestore_client().collection(collection)


def docs2str(docs):  # pragma: no cover
    return ["(%s, %s)" % (doc.id, doc.to_dict()) for doc in docs]
