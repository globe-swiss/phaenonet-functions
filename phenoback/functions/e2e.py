import logging
from http import HTTPStatus

from flask import Request, Response

import phenoback.utils.firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def main(request: Request):  # pylint: disable=unused-argument
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    delete_user_data(["q7lgBm5nm7PUkof20UdZ9D4d0CV2", "JIcn8kFpI4fYYcbdi9QzPlrHomn1"])
    return Response("ok", HTTPStatus.OK)


def delete_user_data(user_ids: str) -> None:
    log.info("Delete all data for %s", user_ids)
    f.delete_batch("individuals", "user", "in", user_ids)
    f.delete_batch("invites", "user", "in", user_ids)
    for user_id in user_ids:
        f.write_document(
            "users",
            user_id,
            {
                "following_individuals": f.DELETE_FIELD,
                "following_users": f.DELETE_FIELD,
            },
            merge=True,
        )
