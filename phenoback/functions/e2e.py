import logging
from http import HTTPStatus

from flask import Request, Response

from phenoback.utils.firestore import delete_batch

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def main(request: Request):  # pylint: disable=unused-argument
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    delete_user_individuals("q7lgBm5nm7PUkof20UdZ9D4d0CV2")
    return Response("ok", HTTPStatus.OK)


def delete_user_individuals(user_id: str) -> None:
    log.info("Delete all individuals for %s", user_id)
    delete_batch("individuals", "user", "==", user_id)
    delete_batch("invites", "user", "==", user_id)
