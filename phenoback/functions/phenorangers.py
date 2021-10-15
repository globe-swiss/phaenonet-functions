import logging
from http import HTTPStatus
from typing import Optional

from flask import Response

from phenoback.utils.data import (
    get_phenoyear,
    get_user_id_by_email,
    query_individuals,
    query_observation,
    update_individual,
    user_exists,
)
from phenoback.utils.firestore import (
    ArrayUnion,
    Transaction,
    get_transaction,
    transactional,
    update_document,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def promote(email: str) -> Response:
    return promote_transactional(get_transaction(), email)


@transactional
def promote_transactional(transaction: Transaction, email: str) -> Response:
    """
    Promotes user to Ranger.
    Fails if user has observations in the current phenoyear.
    Updates any individuals already created in the current phenoyear.
    """
    log.info("promote %s to ranger", email)
    if user_exists(email):
        user = get_user_id_by_email(email)
        year = get_phenoyear()
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
        query_observation("user", "==", user)
        .where("year", "==", year)
        .limit(1)
        .stream()
    ):
        return observation_doc.id
    return None


def update_individuals(user: str, year: int, transaction: Transaction) -> int:
    updated = 0
    for individual_doc in (
        query_individuals("user", "==", user).where("year", "==", year).stream()
    ):
        update_individual(
            individual_doc.id, {"source": "ranger"}, transaction=transaction
        )
        updated += 1
    return updated


def set_ranger(user: str, transaction: Transaction):
    update_document(
        "public_users", user, {"roles": ArrayUnion(["ranger"])}, transaction=transaction
    )
    log.debug("promoted %s to Ranger", user)
