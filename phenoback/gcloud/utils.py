import phenoback
from datetime import datetime
from typing import Union, List

from firebase_admin import firestore
from google.cloud.firestore_v1.client import Client
import dateparser

_db = None


def get_client() -> Client:
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


def get_id(function_context) -> str:
    return function_context.resource.split('/')[-1]


def delete_collection(coll_ref, batch_size=1000):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(u'Deleting doc {} => {}'.format(doc.id, doc.to_dict()))
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


def write_batch(collection: str, key: str, data: List[dict], update: bool = False) -> None:
    batch = get_client().batch()
    cnt = 0
    for item in data:
        cnt += 1
        ref = get_client().collection(collection).document(str(item[key]))
        item.pop(key)
        if update:
            batch.update(ref, item)
        else:
            batch.set(ref, item)
        if cnt == 500:
            batch.commit()
            cnt = 0
    batch.commit()


def write_document(collection: str, document_id: str, data: dict) -> None:
    get_client().collection(collection).document(document_id).set(data)


def get_document(document_path: str) -> dict:
    return get_client().document(document_path).get().to_dict()
