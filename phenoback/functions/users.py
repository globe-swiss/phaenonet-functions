import phenoback
from firebase_admin import firestore
from google.cloud.firestore_v1.client import Client

_db = None


def get_client() -> Client:
    global _db
    if not _db:
        _db = firestore.client()
    return _db


def process_new_nickname(user_id, nickname: str):
    get_client().collection('public_user').document(nickname).set({'user': user_id})


def process_update_nickname(user_id, old_nickname, new_nickname: str):
    process_new_nickname(user_id, new_nickname)
    process_delete_nickname(old_nickname)


def process_delete_nickname(nickname):
    get_client().collection('public_user').document(nickname).delete()
