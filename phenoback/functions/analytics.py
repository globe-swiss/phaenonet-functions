import logging
from datetime import datetime
from typing import Optional

import numpy as np
from google.cloud import firestore

from phenoback.utils.data import get_individual
from phenoback.utils.firestore import DELETE_FIELD, firestore_client, Transaction

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

STATE_COLLECTION = "analytics_state"
RESULT_COLLECTION = "analytics_result"


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
        if altitude_grp:
            state_document["altitude_grp"] = altitude_grp

    state = state_document.get("state")
    state.setdefault(phase, dict())[observation_id] = observation_date
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
    log.debug(
        "Write results: (phase: %s, source: %s, year: %i, species: %s, altitude_grp: %s)",
        phase,
        source,
        year,
        species,
        altitude_grp,
    )
    document_id = get_analytics_document_id(year, species, source, altitude_grp)
    if observation_dates:
        values = {
            phase: {
                "min": np.min(observation_dates),
                "max": np.max(observation_dates),
                "median": np.quantile(observation_dates, 0.5, interpolation="nearest"),
                "quantile_25": np.quantile(
                    observation_dates, 0.25, interpolation="nearest"
                ),
                "quantile_75": np.quantile(
                    observation_dates, 0.75, interpolation="nearest"
                ),
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
    if altitude_grp:
        result_document["altitude_grp"] = altitude_grp
        result_document["type"] = "altitude"
    else:
        result_document["type"] = "species"

    result_ref = firestore_client().collection(RESULT_COLLECTION).document(document_id)
    transaction.set(result_ref, result_document, merge=True)


@firestore.transactional
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


@firestore.transactional
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
        "Remove Observation: (observation_id: %s, phase: %s, source: %s, year: %i, "
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
            "Observation not found in state for removal: (observation_id: %s, source: %s, year: %i, species: %s, "
            "phase: %s)",
            observation_id,
            source,
            year,
            species,
            phase,
        )


def get_altitude_grp(individual_id: str) -> Optional[str]:
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
    if altitude_grp:
        return "%s_%s_%s_%s" % (str(year), species, source, altitude_grp)
    else:
        return "%s_%s_%s" % (str(year), species, source)


def process_observation(
    observation_id: str,
    observation_date: datetime,
    individual_id: str,
    source: str,
    year: int,
    species: str,
    phase: str,
):
    log.info(
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
    if altitude_key:
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
    log.info(
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
    if altitude_key:
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
