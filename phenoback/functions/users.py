from phenoback.utils.firestore import (
    delete_document,
    get_transaction,
    transactional,
    update_document,
    write_document,
)


def process_new_user(user_id: str, nickname: str) -> None:
    _process_new_user_transaction(get_transaction(), user_id, nickname)


@transactional
def _process_new_user_transaction(transaction, user_id, nickname):
    write_document("nicknames", nickname, {"user": user_id}, transaction=transaction)
    write_document(
        "public_users", user_id, {"nickname": nickname}, transaction=transaction
    )


def process_update_nickname(user_id: str, nickname_old: str, nickname_new: str) -> None:
    _process_update_nickname_transaction(
        get_transaction(), user_id, nickname_old, nickname_new
    )


@transactional
def _process_update_nickname_transaction(
    transaction, user_id, nickname_old, nickname_new
):
    write_document(
        "nicknames", nickname_new, {"user": user_id}, transaction=transaction
    )
    update_document(
        "public_users", user_id, {"nickname": nickname_new}, transaction=transaction
    )
    delete_document("nicknames", nickname_old, transaction=transaction)


def process_delete_user(user_id: str, nickname: str) -> None:
    _process_delete_user_transaction(get_transaction(), user_id, nickname)


@transactional
def _process_delete_user_transaction(transaction, user_id, nickname):
    delete_document("nicknames", nickname, transaction=transaction)
    delete_document("public_users", user_id, transaction=transaction)
