from datetime import datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

import tzlocal
from firebase_admin import auth

from phenoback.utils.firestore import (  # pylint: disable=unused-import
    ArrayUnion,
    Query,
    Transaction,
    delete_batch,
    delete_document,
    get_count,
    get_document,
    query_collection,
    update_document,
    write_batch,
    write_document,
)


@lru_cache
def _get_static_config() -> dict:
    return get_document("definitions", "config_static")


@lru_cache
def _get_dynamic_config() -> dict:
    return get_document("definitions", "config_dynamic")


def get_phenophase(species: str, phenophase: str) -> dict:
    return _get_static_config()["species"][species]["phenophases"][phenophase]


def get_species(species: str) -> dict:
    return _get_static_config()["species"][species]


def is_actual_observation(comment: str) -> bool:
    """Check if the comment indicates an actual observation that should be counted in statistics."""
    return _get_static_config()["comments"].get(comment, {"stats": True})["stats"]


def get_phenoyear(reset_cache=False) -> int:
    if reset_cache:
        _get_dynamic_config.cache_clear()
    return _get_dynamic_config()["phenoyear"]


def update_phenoyear(year: int, transaction: Transaction = None) -> None:
    write_document(
        "definitions",
        "config_dynamic",
        {"phenoyear": year},
        merge=True,
        transaction=transaction,
    )
    _get_dynamic_config.cache_clear()


def get_individual(individual_id: str, transaction: Transaction = None) -> dict:
    return get_document("individuals", individual_id, transaction=transaction)


def delete_individual(individual_id: str, transaction: Transaction = None) -> None:
    delete_document("individuals", individual_id, transaction=transaction)


def delete_individuals(field_path: str, op_string: str, value: Any) -> None:
    delete_batch("individuals", field_path, op_string, value)


def query_individuals(field_path: str, op_string: str, value: Any) -> Query:
    return query_collection("individuals", field_path, op_string, value)


def write_individuals(
    individuals: list[dict], key: str, transaction: Transaction = None
) -> None:
    if transaction is not None:
        write_batch("individuals", key, individuals, transaction=transaction)
    else:
        write_batch("individuals", key, individuals)


def write_individual(
    individual_id: str, data: dict, merge: bool = False, transaction: Transaction = None
) -> None:
    write_document(
        "individuals", individual_id, data, merge=merge, transaction=transaction
    )


def update_individual(
    individual_id: str, data: dict, transaction: Transaction = None
) -> None:
    update_document("individuals", individual_id, data, transaction=transaction)


def get_observation(observation_id: str, transaction: Transaction = None) -> dict:
    return get_document("observations", observation_id, transaction=transaction)


def update_observation(
    observation_id: str, data: dict, transaction: Transaction = None
) -> None:
    update_document("observations", observation_id, data, transaction=transaction)


def delete_observation(observation_id: str, transaction: Transaction = None) -> None:
    delete_document("observations", observation_id, transaction=transaction)


def write_observation(
    observation_id: str, data: dict, transaction: Transaction = None
) -> None:
    write_document("observations", observation_id, data, transaction=transaction)


def query_observation(field_path: str, op_string: str, value: Any) -> Query:
    return query_collection("observations", field_path, op_string, value)


def create_user(
    user_id, nickname, firstname="Firstname", lastname="Lastname", locale="de-CH"
):
    write_document(
        "users",
        user_id,
        {
            "firstname": firstname,
            "lastname": lastname,
            "locale": locale,
            "nickname": nickname,
        },
    )


def get_user(user_id: str, transaction: Transaction = None) -> dict:
    return get_document("users", user_id, transaction=transaction)


def get_email(user_id: str) -> str:  # pragma: no cover
    return auth.get_user(user_id).email


def user_exists(email: str) -> bool:  # pragma: no cover
    try:
        auth.get_user_by_email(email)
        return True
    except auth.UserNotFoundError:
        return False


def get_user_id_by_email(email: str) -> str:  # pragma: no cover
    return auth.get_user_by_email(email).uid


def follow_user(
    follower_id: str, followee_id: str, transaction: Transaction = None
) -> bool:
    user = get_user(follower_id, transaction=transaction)
    if not user:
        raise ValueError(f"User not found {follower_id}")
    if followee_id not in user.get("following_users", []):
        update_document(
            "users",
            follower_id,
            {"following_users": ArrayUnion([followee_id])},
            transaction=transaction,
        )
        return True
    else:
        return False


def has_observations(individual: dict) -> bool:
    # last observation date is set for individuals and stations
    return individual.get("last_observation_date") is not None


def has_sensor(individual: dict) -> bool:
    return individual.get("sensor") is not None


def localtime(timestamp: datetime = None):
    if not timestamp:
        timestamp = datetime.now(tz=tzlocal.get_localzone())
    return timestamp.astimezone(ZoneInfo("Europe/Zurich"))


def localdate(timestamp: datetime = None):
    return localtime(timestamp).date()


def to_id_array(data: dict[dict], key="id") -> list[dict]:
    return [{key: k, **v} for k, v in data.items()]
