import logging
from contextlib import contextmanager
from typing import Any, List, Optional

from firebase_admin import firestore
from google.cloud.firestore_v1 import DELETE_FIELD as _DELETE_FIELD
from google.cloud.firestore_v1 import SERVER_TIMESTAMP as _SERVER_TIMESTAMP
from google.cloud.firestore_v1 import ArrayUnion as _ArrayUnion
from google.cloud.firestore_v1 import Increment as _Increment
from google.cloud.firestore_v1 import Query as _Query
from google.cloud.firestore_v1 import transactional as _transactional
from google.cloud.firestore_v1.batch import WriteBatch
from google.cloud.firestore_v1.client import Client as _Client
from google.cloud.firestore_v1.collection import (
    CollectionReference as _CollectionReference,
)
from google.cloud.firestore_v1.transaction import Transaction as _Transaction

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


@contextmanager
def transaction():
    transaction = get_transaction()
    yield transaction
    transaction.commit()


def delete_document(collection: str, document_id: str, trx: Transaction = None) -> None:
    log.debug("Delete document %s from %s", document_id, collection)
    ref = firestore_client().collection(collection).document(document_id)
    if trx:
        trx.delete(ref)
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


def _write_batch(
    collection: str,
    key: str,
    data: List[dict],
    merge: bool,
    commit_size: int,
    writebatch: WriteBatch,
) -> int:
    # pylint: disable=too-many-arguments
    cnt = 0
    for item in data:
        cnt += 1
        ref = firestore_client().collection(collection).document(str(item[key]))
        item.pop(key)
        writebatch.set(ref, item, merge=merge)
        if cnt == commit_size:
            log.debug("Commiting %i documents on %s", cnt, collection)
            writebatch.commit()
            cnt = 0
    if commit_size > 0:
        log.debug("Committing %i documents on %s", cnt, collection)
        writebatch.commit()
        cnt = 0
    return cnt


def write_batch(
    collection: str,
    key: str,
    data: List[dict],
    merge: bool = False,
    batch_size: int = 500,
) -> int:
    log.info("Batch-write %i documents to %s", len(data), collection)
    batch = firestore_client().batch()
    return _write_batch(
        collection, key, data, merge=merge, commit_size=batch_size, writebatch=batch
    )


def write_batch_transaction(
    collection: str,
    key: str,
    data: List[dict],
    trx: Transaction,
    merge: bool = False,
) -> int:
    log.info(
        "Batch-write %i documents to %s within transaction %s",
        len(data),
        collection,
        trx.id,
    )
    return _write_batch(
        collection, key, data, merge=merge, commit_size=-1, writebatch=trx
    )


def write_document(
    collection: str,
    document_id: Optional[str],
    data: dict,
    merge: bool = False,
    trx: Transaction = None,
) -> None:
    log.debug(
        "Write document %s to %s (%s)",
        document_id,
        collection,
        trx.id if trx else None,
    )
    ref = firestore_client().collection(collection).document(document_id)
    if trx:
        trx.set(ref, data, merge=merge)
    else:
        ref.set(data, merge=merge)


def update_document(
    collection: str,
    document_id: str,
    data: dict,
    trx: Transaction = None,
) -> None:
    log.debug(
        "Update document %s in %s (%s)",
        document_id,
        collection,
        trx.id if trx else None,
    )
    ref = firestore_client().collection(collection).document(document_id)
    if trx:
        trx.update(ref, data)
    else:
        ref.update(data)


def get_document(
    collection: str, document_id: str, trx: Transaction = None
) -> Optional[dict]:
    log.debug(
        "Get document %s in %s (%s)",
        document_id,
        collection,
        trx.id if trx else None,
    )
    return (
        firestore_client()
        .collection(collection)
        .document(document_id)
        .get(transaction=trx)
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
