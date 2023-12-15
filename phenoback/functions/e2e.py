import logging
from http import HTTPStatus

from flask import Request, Response

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.functions import phenorangers, users  # exception: allow functions import

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def main_reset(request: Request):  # pylint: disable=unused-argument
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    delete_user_data(["q7lgBm5nm7PUkof20UdZ9D4d0CV2", "JIcn8kFpI4fYYcbdi9QzPlrHomn1"])
    return Response("ok", HTTPStatus.OK)


def main_restore(request: Request):  # pylint: disable=unused-argument
    """
    Restore test users after database copyback
    """
    restore_test_users()
    return Response("ok", HTTPStatus.OK)


def delete_user_data(user_ids: str) -> None:
    log.info("Delete all data for %s", user_ids)
    f.delete_batch("observations", "user", "in", user_ids)
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


def restore_test_users() -> None:
    d.create_user(
        "q7lgBm5nm7PUkof20UdZ9D4d0CV2",
        "e2e-test-nick",
        "e2e-name",
        "e2e-surname",
        "de-CH",
    )
    users.process_new_user("q7lgBm5nm7PUkof20UdZ9D4d0CV2", "e2e-test-nick")
    d.create_user(
        "JIcn8kFpI4fYYcbdi9QzPlrHomn1",
        "e2e-ranger-nick",
        "e2e-ranger-name",
        "e2e-ranger-surname",
        "de-CH",
    )
    users.process_new_user("JIcn8kFpI4fYYcbdi9QzPlrHomn1", "e2e-ranger-nick")
    phenorangers.set_ranger("JIcn8kFpI4fYYcbdi9QzPlrHomn1")
    d.create_user(
        "3NOG91ip31ZdzdIjEdhaoA925U72",
        "ranger-demo",
    )
    users.process_new_user("3NOG91ip31ZdzdIjEdhaoA925U72", "ranger-demo")
    phenorangers.set_ranger("3NOG91ip31ZdzdIjEdhaoA925U72")
