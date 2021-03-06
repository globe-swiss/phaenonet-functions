from functools import lru_cache
from typing import Any, List

from google.cloud.firestore_v1 import Query

from phenoback.utils.firestore import (
    delete_batch,
    delete_document,
    get_document,
    query_collection,
    update_document,
    write_batch,
    write_document,
)


@lru_cache()
def _get_static_config() -> dict:
    return get_document("definitions", "config_static")


@lru_cache()
def _get_dynamic_config() -> dict:
    return get_document("definitions", "config_dynamic")


def get_phenophase(species: str, phenophase: str) -> dict:
    return _get_static_config()["species"][species]["phenophases"][phenophase]


def get_species(species: str) -> dict:
    return _get_static_config()["species"][species]


def get_phenoyear() -> int:
    return _get_dynamic_config()["phenoyear"]


def update_phenoyear(year: int) -> None:
    update_document("definitions", "config_dynamic", {"phenoyear": year})


def get_individual(individual_id: str) -> dict:
    return get_document("individuals", individual_id)


def delete_individual(individual_id: str) -> None:
    delete_document("individuals", individual_id)


def delete_individuals(field_path: str, op_string: str, value: Any) -> None:
    delete_batch("individuals", field_path, op_string, value)


def query_individuals(field_path: str, op_string: str, value: Any) -> Query:
    return query_collection("individuals", field_path, op_string, value)


def write_individuals(individuals: List[dict], key: str) -> None:
    write_batch("individuals", key, individuals)


def write_individual(individual_id: str, data: dict, merge=False) -> None:
    write_document("individuals", individual_id, data, merge=merge)


def update_individual(individual_id: str, data: dict) -> None:
    update_document("individuals", individual_id, data)


def has_observations(individual: dict) -> bool:
    # last observation date is set for individuals and stations
    return individual.get("last_observation_date") is not None


def get_observation(observation_id: str) -> dict:
    return get_document("observations", observation_id)


def update_observation(observation_id: str, data: dict) -> None:
    update_document("observations", observation_id, data)


def delete_observation(observation_id: str) -> None:
    delete_document("observations", observation_id)


def write_observation(observation_id: str, data: dict) -> None:
    write_document("observations", observation_id, data)


def query_observation(field_path: str, op_string: str, value: Any) -> Query:
    return query_collection("observations", field_path, op_string, value)


def get_user(user_id: str) -> dict:
    return get_document("users", user_id)
