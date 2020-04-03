from phenoback.gcloud.utils import *


def process_new_user(user_id: str, nickname: str):
    write_document('nicknames', nickname, {'user': user_id})
    write_document('public_users', user_id, {'nickname': nickname})


def process_update_nickname(user_id: str, old_nickname: str, new_nickname: str):
    write_document('nicknames', new_nickname,  {'user': user_id})
    update_document('public_users', user_id,  {'nickname': new_nickname})
    delete_document('nicknames', old_nickname)


def process_delete_user(user_id: str, nickname: str):
    firestore_client().collection('nicknames').document(nickname).delete()
    firestore_client().collection('public_users').document(user_id).delete()
