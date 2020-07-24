from typing import List, Any, Optional
import logging

from firebase_admin import firestore
from google.cloud.firestore_v1 import Query, DELETE_FIELD
from google.cloud.firestore_v1.client import Client
from google.cloud.firestore_v1.collection import CollectionReference

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_db = None
DELETE_FIELD = DELETE_FIELD


def firestore_client() -> Client:
    global _db
    if not _db:
        _db = firestore.client()
    return _db


def delete_document(collection: str, document_id: str) -> None:
    log.debug('Delete document %s from %s' % (document_id, collection))
    firestore_client().collection(collection).document(document_id).delete()


def _delete_collection(coll_ref, batch_size: int = 1000):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        log.debug('Deleting doc {} => {}'.format(doc.id, doc.to_dict()))
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return _delete_collection(coll_ref, batch_size)


def delete_collection(collection: str, batch_size: int = 1000) -> None:
    _delete_collection(firestore_client().collection(collection), batch_size)


def write_batch(collection: str, key: str, data: List[dict], merge: bool = False) -> None:
    log.info('Batch-write %i documents to %s' % (len(data), collection))
    batch = firestore_client().batch()
    cnt = 0
    for item in data:
        cnt += 1
        ref = firestore_client().collection(collection).document(str(item[key]))
        item.pop(key)
        batch.set(ref, item, merge=merge)
        if cnt == 500:
            log.debug('Commiting %i documents on %s' % (cnt, collection))
            batch.commit()
            cnt = 0
    log.debug('Committing %i documents on %s' % (cnt, collection))
    batch.commit()


def write_document(collection: str, document_id: Optional[str], data: dict, merge: bool = False) -> None:
    log.debug('Write document %s to %s' % (document_id, collection))
    firestore_client().collection(collection).document(document_id).set(data, merge=merge)


def update_document(collection: str, document_id: str, data: dict) -> None:
    log.debug('Update document %s in %s' % (document_id, collection))
    firestore_client().collection(collection).document(document_id).update(data)


def get_document(collection: str, document_id: str) -> Optional[dict]:
    log.debug('Get document %s in %s' % (document_id, collection))
    return firestore_client().collection(collection).document(document_id).get().to_dict()


def query_collection(collection: str, field_path: str, op_string: str, value: Any) -> Query:
    log.debug('Query %s where %s %s %s' % (collection, field_path, op_string, value))
    return firestore_client().collection(collection).where(field_path, op_string, value)


def get_collection(collection: str) -> CollectionReference:
    log.debug('Query collection %s' % collection)
    return firestore_client().collection(collection)
