# pylint: disable=too-many-positional-arguments
import logging
from datetime import datetime
from functools import lru_cache
from http import HTTPStatus

import numpy as np
from flask import Request, Response

from phenoback.utils import gcloud as g
from phenoback.utils import tasks
from phenoback.utils.data import get_individual
from phenoback.utils.firestore import (
    DELETE_FIELD,
    Transaction,
    firestore_client,
    transactional,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

QUEUE_NAME = "analyticupdates"
FUNCTION_NAME = "http_observations_write__analytics"

ANALYTIC_PHENOPHASES = ("BEA", "BLA", "BFA", "BVA", "FRA")
STATE_COLLECTION = "analytics_state"
RESULT_COLLECTION = "analytics_result"


@lru_cache
def client() -> tasks.GCFClient:
    return tasks.GCFClient(QUEUE_NAME, FUNCTION_NAME)


def main_enqueue(data, context):
    phenophase = g.get_field(data, "phenophase", expected=False) or g.get_field(
        data, "phenophase", old_value=True, expected=False
    )
    if phenophase in ANALYTIC_PHENOPHASES:
        client().send({"data": data, "context": g.context2dict(context)})
        log.debug("Enqueue event: phenophase=%s", phenophase)
    else:
        log.debug("Skip event: phenophase=%s", phenophase)


def main_process(request: Request):
    request_json = request.get_json(silent=True)
    main(request_json["data"], g.dict2context(request_json["context"]))
    return Response("accepted", HTTPStatus.ACCEPTED)


def main(data, context):
    if g.is_create_event(data):
        _main_create(data, context)
    elif g.is_update_event(data):
        _main_update(data, context)
    elif g.is_delete_event(data):
        _main_delete(data, context)
    else:  # pragma: no cover
        log.error("Unknown event type")


def _main_create(data, context):
    """
    Updates analytic values in Firestore when an observation is created in Firestore.
    """
    observation_id = g.get_document_id(context)
    phenophase = g.get_field(data, "phenophase")
    individual_id = g.get_field(data, "individual_id")
    source = g.get_field(data, "source")
    year = g.get_field(data, "year")
    species = g.get_field(data, "species")
    observation_date = g.get_field(data, "date")

    if phenophase in ANALYTIC_PHENOPHASES:
        log.info(
            "Process analytic values for %s, phenophase %s",
            observation_id,
            phenophase,
        )
        process_observation(
            observation_id,
            observation_date,
            individual_id,
            source,
            year,
            species,
            phenophase,
        )
    else:
        log.debug(
            "No analytic values processed for %s, phenophase %s",
            observation_id,
            phenophase,
        )


def _main_update(data, context):
    """
    Updates analytical values in Firestore if the observation date was modified on a observation document.
    """
    if g.is_field_updated(data, "date") or g.is_field_updated(data, "reprocess"):
        _main_create(data, context)


def _main_delete(data, context):
    """
    Updates analytical values in Firestore if an observation was deleted.
    """
    observation_id = g.get_document_id(context)
    phenophase = g.get_field(data, "phenophase", old_value=True)
    individual_id = g.get_field(data, "individual_id", old_value=True)
    source = g.get_field(data, "source", old_value=True)
    year = g.get_field(data, "year", old_value=True)
    species = g.get_field(data, "species", old_value=True)

    if phenophase in ANALYTIC_PHENOPHASES:
        log.info("Remove analytic values for observation %s", observation_id)
        process_remove_observation(
            observation_id,
            individual_id,
            source,
            year,
            species,
            phenophase,
        )
    else:
        log.debug(
            "No analytic values processed for %s, phenophase %s",
            observation_id,
            phenophase,
        )


def update_state(
    transaction: Transaction,
    observation_id: str,
    observation_date: datetime,
    phase: str,
    source: str,
    year: int,
    species: str,
    altitude_grp: str = None,
) -> list:
    """
    Updates the phenodate in the state collection. Needs to be done in a transactions as the state document
    might be changed simultaniously, e.g. importing many documents from meteoswiss.
    """
    log.debug(
        "Update state: (observation_id: %s, observation_date: %s, phase: %s, source: %s, year: %i, "
        "species: %s, altitude_grp: %s)",
        observation_id,
        observation_date,
        phase,
        source,
        year,
        species,
        altitude_grp,
    )
    document_id = get_analytics_document_id(year, species, source, altitude_grp)
    state_ref = firestore_client().collection(STATE_COLLECTION).document(document_id)
    state_document = state_ref.get(transaction=transaction).to_dict()
    if not state_document:
        state_document = {
            "source": source,
            "year": year,
            "species": species,
            "state": {},
        }
        if altitude_grp is not None:
            state_document["altitude_grp"] = altitude_grp

    state = state_document.get("state")
    state.setdefault(phase, {})[observation_id] = observation_date
    transaction.set(
        state_ref, state_document
    )  # optimize: set->update if document existed
    return list(state[phase].values())


def update_result(
    transaction: Transaction,
    observation_dates: list,
    phase: str,
    source: str,
    year: int,
    species: str,
    altitude_grp: str = None,
) -> None:
    # log.debug(
    #     "Write results: (phase: %s, source: %s, year: %i, species: %s, altitude_grp: %s)",
    #     phase,
    #     source,
    #     year,
    #     species,
    #     altitude_grp,
    # )
    document_id = get_analytics_document_id(year, species, source, altitude_grp)
    if observation_dates:
        values = {
            phase: {
                "min": np.min(observation_dates),
                "max": np.max(observation_dates),
                "median": np.quantile(observation_dates, 0.5, method="nearest"),
                "quantile_25": np.quantile(observation_dates, 0.25, method="nearest"),
                "quantile_75": np.quantile(observation_dates, 0.75, method="nearest"),
            }
        }
    else:  # delete phase results if has no values
        values = {phase: DELETE_FIELD}
    result_document = {
        "source": source,
        "year": year,
        "species": species,
        "values": values,
    }
    if altitude_grp is not None:
        result_document["altitude_grp"] = altitude_grp
        result_document["type"] = "altitude"
    else:
        result_document["type"] = "species"

    result_ref = firestore_client().collection(RESULT_COLLECTION).document(document_id)
    transaction.set(result_ref, result_document, merge=True)


@transactional
def update_data(
    transaction: Transaction,
    observation_id: str,
    observation_date: datetime,
    year: int,
    species: str,
    phase: str,
    source: str,
    altitude_grp: str = None,
) -> None:
    observation_dates = update_state(
        transaction,
        observation_id,
        observation_date,
        phase,
        source,
        year,
        species,
        altitude_grp,
    )
    update_result(
        transaction, observation_dates, phase, source, year, species, altitude_grp
    )


@transactional
def remove_observation(
    transaction: Transaction,
    observation_id: str,
    year: int,
    species: str,
    phase: str,
    source: str,
    altitude_grp: str = None,
) -> None:
    log.debug(
        "Remove Observation state (observation_id: %s, phase: %s, source: %s, year: %i, "
        "species: %s, altitude_grp: %s)",
        observation_id,
        phase,
        source,
        year,
        species,
        altitude_grp,
    )
    try:
        document_id = get_analytics_document_id(year, species, source, altitude_grp)
        state_ref = (
            firestore_client().collection(STATE_COLLECTION).document(document_id)
        )
        state_document = state_ref.get(transaction=transaction).to_dict()
        if not state_document:
            log.error(
                "State document %s not found for observation removal: (observation_id: %s, source: %s, "
                "year: %i, species: %s, phase: %s)",
                document_id,
                observation_id,
                source,
                year,
                species,
                phase,
            )
            return
        state = state_document["state"]
        state[phase].pop(observation_id)
        if not state[phase]:  # remove phase if last value removed
            state.pop(phase)

        transaction.set(
            state_ref, state_document
        )  # optimize: set->update if document existed

        observation_dates = list(state.setdefault(phase, {}).values())
        update_result(
            transaction, observation_dates, phase, source, year, species, altitude_grp
        )
    except KeyError:
        log.error(
            "Observation not found in state document for removal: (observation_id: %s, source: %s, year: %i, species: %s, "
            "phase: %s)",
            observation_id,
            source,
            year,
            species,
            phase,
        )


def get_altitude_grp(individual_id: str) -> str | None:
    individual = get_individual(individual_id)
    if not individual:
        log.error("Individual %s not found to lookup altitude group", individual_id)
        return None
    altitude = individual.get("altitude", None)
    altitude_key = None
    if altitude is not None:
        if altitude < 500:
            altitude_key = "alt1"
        elif altitude < 800:
            altitude_key = "alt2"
        elif altitude < 1000:
            altitude_key = "alt3"
        elif altitude < 1200:
            altitude_key = "alt4"
        else:
            altitude_key = "alt5"
    else:
        log.error("no altitude found for individual %s", individual_id)
    return altitude_key


def get_analytics_document_id(
    year: int, species: str, source: str, altitude_grp: str = None
) -> str:
    if altitude_grp is not None:
        return f"{year}_{species}_{source}_{altitude_grp}"
    else:
        return f"{year}_{species}_{source}"


def process_observation(
    observation_id: str,
    observation_date: datetime,
    individual_id: str,
    source: str,
    year: int,
    species: str,
    phase: str,
):
    log.debug(
        "Process observation: (observation_id: %s, observation_date: %s, individual_id: %s, source: %s, "
        "year: %i, species: %s, phase: %s)",
        observation_id,
        observation_date,
        individual_id,
        source,
        year,
        species,
        phase,
    )
    update_data(
        transaction=firestore_client().transaction(),
        observation_id=observation_id,
        observation_date=observation_date,
        year=year,
        species=species,
        phase=phase,
        source=source,
    )
    update_data(
        transaction=firestore_client().transaction(),
        observation_id=observation_id,
        observation_date=observation_date,
        year=year,
        species=species,
        phase=phase,
        source="all",
    )

    altitude_key = get_altitude_grp(individual_id)
    if altitude_key is not None:
        update_data(
            transaction=firestore_client().transaction(),
            observation_id=observation_id,
            observation_date=observation_date,
            year=year,
            species=species,
            phase=phase,
            source=source,
            altitude_grp=altitude_key,
        )
        update_data(
            transaction=firestore_client().transaction(),
            observation_id=observation_id,
            observation_date=observation_date,
            year=year,
            species=species,
            phase=phase,
            source="all",
            altitude_grp=altitude_key,
        )


def process_remove_observation(
    observation_id: str,
    individual_id: str,
    source: str,
    year: int,
    species: str,
    phase: str,
):
    log.debug(
        "Remove observation: (observation_id: %s,  individual_id: %s, source: %s, "
        "year: %i, species: %s, phase: %s)",
        observation_id,
        individual_id,
        source,
        year,
        species,
        phase,
    )
    remove_observation(
        transaction=firestore_client().transaction(),
        observation_id=observation_id,
        year=year,
        species=species,
        phase=phase,
        source=source,
    )
    remove_observation(
        transaction=firestore_client().transaction(),
        observation_id=observation_id,
        year=year,
        species=species,
        phase=phase,
        source="all",
    )

    altitude_key = get_altitude_grp(individual_id)
    if altitude_key is not None:
        remove_observation(
            transaction=firestore_client().transaction(),
            observation_id=observation_id,
            year=year,
            species=species,
            phase=phase,
            source=source,
            altitude_grp=altitude_key,
        )
        remove_observation(
            transaction=firestore_client().transaction(),
            observation_id=observation_id,
            year=year,
            species=species,
            phase=phase,
            source="all",
            altitude_grp=altitude_key,
        )
    else:
        log.error(
            "Altitude key for observation %s not found. "
            "Observation might not have been removed from statistics correctly.",
            observation_id,
        )
