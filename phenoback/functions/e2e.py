import logging

from phenoback.utils.firestore import delete_batch

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def delete_user_individuals(user_id: str) -> None:
    log.info("Delete all individuals for %s", user_id)
    delete_batch("individuals", "user", "==", user_id)
    delete_batch("invites", "user", "==", user_id)
