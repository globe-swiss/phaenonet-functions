import logging
from functools import cache
from typing import Any

import phenoback.utils.data as d
import phenoback.utils.firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

AVAILABLE_PHENOPHASES = {"BEA", "BES", "BFA", "BLA", "BLB", "BVA", "BVS", "FRA"}


@cache
def get_altitude_grp(individual_id: str) -> str:
    individual = d.get_individual(individual_id)
    if not individual:
        log.error("Individual %s not found to lookup altitude group", individual_id)
        raise KeyError(individual_id)

    altitude = individual.get("altitude")
    if altitude is None:
        log.error("No altitude found for individual %s", individual_id)
        raise ValueError(individual_id)

    if altitude < 500:
        return "alt1"
    elif altitude < 800:
        return "alt2"
    elif altitude < 1000:
        return "alt3"
    elif altitude < 1200:
        return "alt4"
    return "alt5"


@cache
def load_observations(phenoyear: int) -> list[dict[str, Any]]:
    """
    Returns all observations for the given year that are relevant for statistics.
    Excludes observations with comments that should not be counted.
    """
    result = [
        doc.to_dict()
        for doc in d.query_observation("year", "==", phenoyear)
        .where(filter=f.FieldFilter("phenophase", "in", AVAILABLE_PHENOPHASES))
        .stream()
        if d.is_actual_observation(doc.to_dict().get("comment"))
    ]
    log.debug("Loaded %i observations for phenoyear %i", len(result), phenoyear)
    return result


def get_observations(phenoyear: int, phenophases: set[str]) -> list[dict[str, Any]]:
    """
    Returns observations for the given year and specified phenophases.
    Only includes observations that are relevant for statistics and match the given phenophases.
    """
    invalid_phases = phenophases - set(AVAILABLE_PHENOPHASES)
    if invalid_phases:
        raise ValueError(
            f"Invalid phenophases requested: {invalid_phases}. Observations only loaded for: {AVAILABLE_PHENOPHASES}"
        )
    return [
        obs
        for obs in load_observations(phenoyear)
        if obs.get("phenophase") in phenophases
    ]


def cache_clear():
    get_altitude_grp.cache_clear()
    load_observations.cache_clear()
