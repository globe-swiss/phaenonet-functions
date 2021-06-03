from phenoback.utils.firestore import (
    delete_document,
    transaction,
    transactional,
    update_document,
    write_document,
)


def process_new_user(user_id: str, nickname: str) -> None:
    with transaction() as trx:
        _process_new_user_trx(trx, user_id, nickname)


@transactional
def _process_new_user_trx(trx, user_id, nickname):
    write_document("nicknames", nickname, {"user": user_id}, trx=trx)
    write_document("public_users", user_id, {"nickname": nickname}, trx=trx)


def process_update_nickname(user_id: str, nickname_old: str, nickname_new: str) -> None:
    with transaction() as trx:
        _process_update_nickname_trx(trx, user_id, nickname_old, nickname_new)


@transactional
def _process_update_nickname_trx(trx, user_id, nickname_old, nickname_new):
    write_document("nicknames", nickname_new, {"user": user_id}, trx=trx)
    update_document("public_users", user_id, {"nickname": nickname_new}, trx=trx)
    delete_document("nicknames", nickname_old, trx=trx)


def process_delete_user(user_id: str, nickname: str) -> None:
    with transaction() as trx:
        _process_delete_user_trx(trx, user_id, nickname)


@transactional
def _process_delete_user_trx(trx, user_id, nickname):
    delete_document("nicknames", nickname, trx=trx)
    delete_document("public_users", user_id, trx=trx)
