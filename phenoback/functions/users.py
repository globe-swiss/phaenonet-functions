import logging

from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def main(data, context):
    user_id = g.get_document_id(context)

    if g.is_update_event(data) and g.is_field_updated(data, "nickname"):
        log.info("update nickname for %s", user_id)
        process_update_nickname(
            user_id,
            g.get_field(data, "nickname", old_value=True),
            g.get_field(data, "nickname"),
        )
    elif g.is_delete_event(data):
        log.info("delete user %s", user_id)
        process_delete_user(user_id, g.get_field(data, "nickname", old_value=True))
    elif g.is_create_event(data):
        log.info("create user %s", user_id)
        process_new_user(user_id, g.get_field(data, "nickname"))
    else:
        log.debug("Nothing to do for %s", user_id)


def process_new_user(user_id: str, nickname: str) -> None:
    _process_new_user_transaction(f.get_transaction(), user_id, nickname)


@f.transactional
def _process_new_user_transaction(transaction, user_id, nickname):
    f.write_document("nicknames", nickname, {"user": user_id}, transaction=transaction)
    f.write_document(
        "public_users", user_id, {"nickname": nickname}, transaction=transaction
    )


def process_update_nickname(user_id: str, nickname_old: str, nickname_new: str) -> None:
    _process_update_nickname_transaction(
        f.get_transaction(), user_id, nickname_old, nickname_new
    )


@f.transactional
def _process_update_nickname_transaction(
    transaction, user_id, nickname_old, nickname_new
):
    f.write_document(
        "nicknames", nickname_new, {"user": user_id}, transaction=transaction
    )
    f.update_document(
        "public_users", user_id, {"nickname": nickname_new}, transaction=transaction
    )
    f.delete_document("nicknames", nickname_old, transaction=transaction)


def process_delete_user(user_id: str, nickname: str) -> None:
    _process_delete_user_transaction(f.get_transaction(), user_id, nickname)


@f.transactional
def _process_delete_user_transaction(transaction, user_id, nickname):
    f.delete_document("nicknames", nickname, transaction=transaction)
    f.delete_document("public_users", user_id, transaction=transaction)
