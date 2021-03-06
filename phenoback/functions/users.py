from phenoback.utils.firestore import delete_document, update_document, write_document


def process_new_user(user_id: str, nickname: str):
    write_document("nicknames", nickname, {"user": user_id})
    write_document("public_users", user_id, {"nickname": nickname})


def process_update_nickname(user_id: str, nickname_old: str, nickname_new: str):
    write_document("nicknames", nickname_new, {"user": user_id})
    update_document("public_users", user_id, {"nickname": nickname_new})
    delete_document("nicknames", nickname_old)


def process_delete_user(user_id: str, nickname: str):
    delete_document("nicknames", nickname)
    delete_document("public_users", user_id)
