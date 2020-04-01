import tempfile

import phenoback
from datetime import datetime
from typing import Union, List, Optional

from firebase_admin import firestore, storage
from google.cloud.firestore_v1.client import Client
from google.cloud.storage.bucket import Bucket
import dateparser

_db = None


def firestore_client() -> Client:
    global _db
    if not _db:
        _db = firestore.client()
    return _db


def get_field(data, fieldname, old_value=False) -> Union[str, int, datetime, None]:
    value_type = 'oldValue' if old_value else 'value'
    value_dict = data[value_type].get('fields', {}).get(fieldname)
    if value_dict:
        value = next(iter(value_dict.values()))
        value_type = next(iter(value_dict.keys()))
        if value_type == 'stringValue':
            return str(value)
        elif value_type == 'integerValue':
            return int(value)
        elif value_type == 'timestampValue':
            return dateparser.parse(value)
        else:
            print("WARN: Unknown field type %s, returning str representation: %s" % (value_type, str(value)))
            return str(value)
    else:
        print("WARN: field %s not found in data %s" % (fieldname, str(data)))


def get_document_id(context) -> str:
    return context.resource.split('/')[-1]


def get_collection_path(context) -> str:
    return '/'.join(context.resource.split('/')[5:-1])


def is_create_event(data: dict) -> bool:
    return len(data['value']) > 0 and len(data['oldValue']) == 0


def is_update_event(data: dict) -> bool:
    return len(data['value']) > 0 and len(data['oldValue']) > 0


def is_delete_event(data: dict) -> bool:
    return len(data['value']) == 0 and len(data['oldValue']) > 0


def is_field_updated(data: dict, fieldname) -> bool:
    return fieldname in data.get('updateMask', {}).get('fieldPaths', [])


def delete_document(collection, document_id):
    firestore_client().collection(collection).document(document_id).delete()


def delete_collection(coll_ref, batch_size=1000):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(u'Deleting doc {} => {}'.format(doc.id, doc.to_dict()))
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


def write_batch(collection: str, key: str, data: List[dict], merge: bool = False) -> None:
    batch = firestore_client().batch()
    cnt = 0
    for item in data:
        cnt += 1
        ref = firestore_client().collection(collection).document(str(item[key]))
        item.pop(key)
        batch.set(ref, item, merge=merge)
        if cnt == 500:
            batch.commit()
            cnt = 0
    batch.commit()


def write_document(collection: str, document_id: str, data: dict, merge: bool = False) -> None:
    firestore_client().collection(collection).document(document_id).set(data, merge=merge)


def update_document(collection: str, document_id: str, data: dict) -> None:
    firestore_client().collection(collection).document(document_id).update(data)


def get_document(document_path: str) -> dict:
    return firestore_client().document(document_path).get().to_dict()


def download_file(bucket: str, path: str):
    blob = storage.bucket(bucket).get_blob(path)
    file = tempfile.TemporaryFile()
    if blob:
        blob.download_to_file(file)
        return file


def upload_file(bucket: str, path: str, file, content_type=None):
    file.seek(0)
    storage.bucket(bucket).blob(path).upload_from_file(file, content_type=content_type)

