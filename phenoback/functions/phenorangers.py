import logging
from http import HTTPStatus
from typing import Optional

from flask import Request, Response

import phenoback.utils.data as d
import phenoback.utils.firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def main(request: Request):
    content_type = request.headers["content-type"]
    if content_type == "application/json":
        request_json = request.get_json(silent=True)
        if not (request_json and "email" in request_json):
            msg = "JSON is invalid, or missing a 'email' property"
            log.warning(msg)
            return Response(msg, HTTPStatus.BAD_REQUEST)
    else:
        msg = f"Unknown content type: {content_type}, application/json required"
        return Response(msg, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    return promote(request_json["email"])


def promote(email: str) -> Response:
    return promote_transactional(f.get_transaction(), email)


@f.transactional
def promote_transactional(transaction: f.Transaction, email: str) -> Response:
    """
    Promotes user to Ranger.
    Fails if user has observations in the current phenoyear.
    Updates any individuals already created in the current phenoyear.
    """
    log.info("promote %s to ranger", email)
    if d.user_exists(email):
        user = d.get_user_id_by_email(email)
        year = d.get_phenoyear()
        observation_id = get_observation(user, year)
        if observation_id:
            msg = f"User {user} with email {email} has observations in {year}. ({observation_id})"
            log.warning(msg)
            return Response(
                msg,
                HTTPStatus.CONFLICT,
            )
        set_ranger(user, transaction=transaction)
        num_updates = update_individuals(user, year, transaction=transaction)
        if num_updates:
            msg = f"Updated {num_updates} individuals."
            log.info(msg)
            return Response(msg, HTTPStatus.OK)
        else:
            return Response("ok", HTTPStatus.OK)
    else:
        msg = f"No user with email {email} found."
        log.warning(msg)
        return Response(msg, HTTPStatus.NOT_FOUND)


def get_observation(user: str, year) -> Optional[str]:
    for observation_doc in (
        d.query_observation("user", "==", user)
        .where(filter=f.FieldFilter("year", "==", year))
        .limit(1)
        .stream()
    ):
        return observation_doc.id
    return None


def update_individuals(user: str, year: int, transaction: f.Transaction) -> int:
    updated = 0
    for individual_doc in (
        d.query_individuals("user", "==", user)
        .where(filter=f.FieldFilter("year", "==", year))
        .stream()
    ):
        d.update_individual(
            individual_doc.id, {"source": "ranger"}, transaction=transaction
        )
        updated += 1
    return updated


def set_ranger(user: str, transaction: f.Transaction):
    f.update_document(
        "public_users",
        user,
        {"roles": f.ArrayUnion(["ranger"])},
        transaction=transaction,
    )
    log.debug("promoted %s to Ranger", user)
