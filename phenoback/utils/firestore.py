import logging
from contextlib import contextmanager
from time import sleep
from typing import Any

from firebase_admin import firestore
from google.cloud.firestore_v1 import DELETE_FIELD as _DELETE_FIELD
from google.cloud.firestore_v1 import SERVER_TIMESTAMP as _SERVER_TIMESTAMP
from google.cloud.firestore_v1 import ArrayUnion as _ArrayUnion
from google.cloud.firestore_v1 import Increment as _Increment
from google.cloud.firestore_v1 import Query as _Query
from google.cloud.firestore_v1 import transactional as _transactional
from google.cloud.firestore_v1.base_query import FieldFilter as _FieldFilter
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
FieldFilter = _FieldFilter


def firestore_client() -> Client:
    global _db  # pylint: disable=invalid-name,global-statement
    if not _db:  # pragma: no cover
        _db = firestore.client()
    return _db


def get_transaction():
    return firestore_client().transaction()


@contextmanager
def transaction_commit():
    transaction = get_transaction()
    yield transaction
    transaction.commit()


def delete_document(
    collection: str, document_id: str, transaction: Transaction = None
) -> None:
    log.debug("Delete document %s from %s", document_id, collection)
    ref = firestore_client().collection(collection).document(document_id)
    if transaction is not None:
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


def _write_batch(
    collection: str,
    key: str,
    data: list[dict],
    *,
    merge: bool,
    commit_size: int,
    writebatch: WriteBatch,
    commit_sleep: float = 0,
) -> int:
    cnt = 0
    for item in data:
        cnt += 1
        ref = firestore_client().collection(collection).document(str(item[key]))
        item.pop(key)
        writebatch.set(ref, item, merge=merge)
        if cnt == commit_size:
            log.debug("Commiting %i documents on %s", cnt, collection)
            writebatch.commit()
            sleep(commit_sleep)
            cnt = 0
    if commit_size > 0:
        log.debug("Committing %i documents on %s", cnt, collection)
        writebatch.commit()
        cnt = 0
    return cnt


def write_batch(
    collection: str,
    key: str,
    data: list[dict],
    *,
    merge: bool = False,
    commit_size: int = None,
    transaction: Transaction = None,
    commit_sleep: float = 0,
) -> int:
    if transaction is not None:
        log.info(
            "Batch-write %i documents to %s within transaction",
            len(data),
            collection,
        )
        if commit_size is not None:  # pragma: no cover
            log.warning(
                "Commit-size cannot be set if writing to transaction, ignoring value (%s)",
                commit_size,
            )
        commit_size = -1
        writebatch = transaction
    else:
        if commit_size is None:
            commit_size = 500
        log.info(
            "Batch-write %i documents to %s in %i batches",
            len(data),
            collection,
            commit_size,
        )
        writebatch = firestore_client().batch()
    return _write_batch(
        collection,
        key,
        data,
        merge=merge,
        commit_size=commit_size,
        commit_sleep=commit_sleep,
        writebatch=writebatch,
    )


def write_document(
    collection: str,
    document_id: str | None,
    data: dict,
    merge: bool = False,
    transaction: Transaction = None,
) -> None:
    log.debug(
        "Write document %s to %s (%s)",
        document_id,
        collection,
        transaction.id if transaction is not None else None,
    )
    ref = firestore_client().collection(collection).document(document_id)
    if transaction is not None:
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
        transaction.id if transaction is not None else None,
    )
    ref = firestore_client().collection(collection).document(document_id)
    if transaction is not None:
        transaction.update(ref, data)
    else:
        ref.update(data)


def get_document(
    collection: str, document_id: str, transaction: Transaction = None
) -> dict | None:
    log.debug(
        "Get document %s in %s (%s)",
        document_id,
        collection,
        transaction.id if transaction is not None else None,
    )
    return (
        firestore_client()
        .collection(collection)
        .document(document_id)
        .get(transaction=transaction)
        .to_dict()
    )


def collection(collection: str) -> Query:
    log.debug("Query %s", collection)
    return firestore_client().collection(collection)


def query_collection(
    collection: str, field_path: str, op_string: str, value: Any
) -> Query:
    log.debug("Query %s where %s %s %s", collection, field_path, op_string, value)
    return (
        firestore_client()
        .collection(collection)
        .where(filter=FieldFilter(field_path, op_string, value))
    )


def get_collection(collection: str) -> CollectionReference:
    log.debug("Query collection %s", collection)
    return firestore_client().collection(collection)


def get_collection_documents(collection: str) -> list[dict]:
    return [location.to_dict() for location in get_collection(collection).stream()]


def docs2str(docs):  # pragma: no cover
    return [f"({doc.id}, {doc.to_dict()})" for doc in docs]
