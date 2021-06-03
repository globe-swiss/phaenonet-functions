from functools import lru_cache
from typing import Any, List

from firebase_admin import auth

from phenoback.utils.firestore import (
    ArrayUnion,
    Query,
    delete_batch,
    delete_document,
    get_document,
    query_collection,
    update_document,
    write_batch,
    write_batch_transaction,
    write_document,
)


@lru_cache()
def _get_static_config() -> dict:
    return get_document("definitions", "config_static")


def _get_dynamic_config() -> dict:
    return get_document("definitions", "config_dynamic")


def get_phenophase(species: str, phenophase: str) -> dict:
    return _get_static_config()["species"][species]["phenophases"][phenophase]


def get_species(species: str) -> dict:
    return _get_static_config()["species"][species]


def get_phenoyear() -> int:
    return _get_dynamic_config()["phenoyear"]


def update_phenoyear(year: int, trx=None) -> None:
    write_document(
        "definitions", "config_dynamic", {"phenoyear": year}, merge=True, trx=trx
    )


def get_individual(individual_id: str, trx=None) -> dict:
    return get_document("individuals", individual_id, trx=trx)


def delete_individual(individual_id: str, trx=None) -> None:
    delete_document("individuals", individual_id, trx=trx)


def delete_individuals(field_path: str, op_string: str, value: Any) -> None:
    delete_batch("individuals", field_path, op_string, value)


def query_individuals(field_path: str, op_string: str, value: Any) -> Query:
    return query_collection("individuals", field_path, op_string, value)


def write_individuals(individuals: List[dict], key: str, trx=None) -> None:
    if trx:
        write_batch_transaction("individuals", key, individuals, trx=trx)
    else:
        write_batch("individuals", key, individuals)


def write_individual(individual_id: str, data: dict, merge=False, trx=None) -> None:
    write_document("individuals", individual_id, data, merge=merge, trx=trx)


def update_individual(individual_id: str, data: dict, trx=None) -> None:
    update_document("individuals", individual_id, data, trx=trx)


def has_observations(individual: dict) -> bool:
    # last observation date is set for individuals and stations
    return individual.get("last_observation_date") is not None


def get_observation(observation_id: str, trx=None) -> dict:
    return get_document("observations", observation_id, trx=trx)


def update_observation(observation_id: str, data: dict, trx=None) -> None:
    update_document("observations", observation_id, data, trx=trx)


def delete_observation(observation_id: str, trx=None) -> None:
    delete_document("observations", observation_id, trx=trx)


def write_observation(observation_id: str, data: dict, trx=None) -> None:
    write_document("observations", observation_id, data, trx=trx)


def query_observation(field_path: str, op_string: str, value: Any) -> Query:
    return query_collection("observations", field_path, op_string, value)


def get_user(user_id: str, trx=None) -> dict:
    return get_document("users", user_id, trx=trx)


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


def follow_user(follower_id: str, followee_id: str, trx=None) -> bool:
    user = get_user(follower_id, trx=trx)
    if not user:
        raise ValueError("User not found %s" % follower_id)
    if followee_id not in user.get("following_users", []):
        update_document(
            "users",
            follower_id,
            {"following_users": ArrayUnion([followee_id])},
            trx=trx,
        )
        return True
    else:
        return False
