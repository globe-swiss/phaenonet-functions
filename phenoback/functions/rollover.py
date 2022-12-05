import logging
from typing import List

from phenoback.functions.iot import app
from phenoback.utils.data import (
    delete_individual,
    get_phenoyear,
    has_observations,
    query_individuals,
    update_phenoyear,
    write_individuals,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_rollover_individuals(
    source_phenoyear: int,
    target_phenoyear: int,
    individual: str = None,
) -> List[dict]:
    """
    Copy individuals to a new phenoyear, removing all fields that are specific for the phenoyear.
    :param source_phenoyear:
    :param target_phenoyear:
    :return:
    """
    new_individuals = []
    query = query_individuals("year", "==", source_phenoyear)
    if individual is not None:  # debuging or fixing
        query = query.where("individual", "==", individual)
    for individual_doc in query.stream():
        individual = individual_doc.to_dict()
        if individual["source"] != "meteoswiss":
            individual["id"] = f'{target_phenoyear}_{individual["individual"]}'
            individual["year"] = target_phenoyear
            for key in [
                "last_phenophase",
                "last_observation_date",
                "created",
                "modified",
                "sensor",
                "reprocess",
            ]:
                individual.pop(key, None)
            new_individuals.append(individual)
            log.debug("marking individual %s for rollover", individual)
    return new_individuals


def get_stale_individuals(year: int) -> List[str]:
    """
    Remove all individuals in Firestore that have no observations for all
    sources (globe and meteoswiss) for the given phenoyear year.
    :param year: the phenoyear
    """
    stale_list = []
    # split querying and deleting to avoid stream timeouts
    for individual_doc in query_individuals("year", "==", year).stream():
        if not has_observations(individual_doc.to_dict()):
            stale_list.append(individual_doc.id)
    return stale_list


def rollover():
    source_phenoyear = get_phenoyear()
    target_phenoyear = source_phenoyear + 1
    log.info(
        "Gather rollover individuals of %i to %i", source_phenoyear, target_phenoyear
    )
    new_individuals = get_rollover_individuals(source_phenoyear, target_phenoyear)

    log.info("Gather stale individuals for %i", source_phenoyear)
    stale_individuals = get_stale_individuals(source_phenoyear)

    log.info(
        "Creating %i new individuals in %i", len(new_individuals), target_phenoyear
    )
    write_individuals(new_individuals, "id")

    log.info(
        "Remove %i stale individuals for %i", len(stale_individuals), source_phenoyear
    )
    for individual_id in stale_individuals:
        log.debug("Remove individual %s", individual_id)
        delete_individual(individual_id)

    cleared_sensors = app.clear_sensors(source_phenoyear)
    log.info(
        "Cleared %i sensors from individuals for %i", cleared_sensors, source_phenoyear
    )

    log.info(
        "Setting current phenoyear from %i to %i", source_phenoyear, target_phenoyear
    )
    update_phenoyear(target_phenoyear)
