import logging

from phenoback.functions import map as pheno_map
from phenoback.functions import statistics
from phenoback.functions.iot import app
from phenoback.utils import data as d
from phenoback.utils import firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

SOURCE_ROLLOVER_MAPPING = {
    "globe": True,
    "meteoswiss": False,
    "wld": False,
    "ranger": True,
}


def main(data, context):  # pylint: disable=unused-argument
    rollover()


def does_rollover(individual: dict) -> bool:
    source = individual.get("source")
    try:
        return SOURCE_ROLLOVER_MAPPING[source]
    except KeyError as ex:
        msg = f"Rollover rule for source '{source}' is not defined for {individual}"
        log.error(msg)
        raise ValueError(msg) from ex


def get_rollover_individuals(
    source_phenoyear: int,
    target_phenoyear: int,
    individual: str = None,
) -> list[dict]:
    """
    Copy individuals to a new phenoyear, removing all fields that are specific for the phenoyear.
    :param source_phenoyear:
    :param target_phenoyear:
    :return:
    """
    new_individuals = []
    query = d.query_individuals("year", "==", source_phenoyear)
    if individual is not None:  # debuging or fixing
        query = query.where(filter=f.FieldFilter("individual", "==", individual))
    for individual_doc in query.stream():
        individual = individual_doc.to_dict()
        if does_rollover(individual):
            individual["id"] = f'{target_phenoyear}_{individual["individual"]}'
            individual["year"] = target_phenoyear
            for key in [
                "last_phenophase",
                "last_observation_date",
                "created",
                "modified",
                "reprocess",
            ]:
                individual.pop(key, None)
            if individual.get("sensor"):
                individual["sensor"] = {}
            new_individuals.append(individual)
            log.debug("marking individual %s for rollover", individual)
    return new_individuals


def rollover():
    source_phenoyear = d.get_phenoyear()
    target_phenoyear = source_phenoyear + 1
    log.info(
        "Gather rollover individuals of %i to %i", source_phenoyear, target_phenoyear
    )
    new_individuals = get_rollover_individuals(source_phenoyear, target_phenoyear)

    log.info("Create maps document for %i", target_phenoyear)
    pheno_map.init(target_phenoyear)

    log.info(
        "Creating %i new individuals in %i", len(new_individuals), target_phenoyear
    )
    d.write_individuals(new_individuals, "id")

    cleared_sensors = app.clear_sensors(source_phenoyear)
    log.info(
        "Cleared %i sensors from individuals for %i", cleared_sensors, source_phenoyear
    )

    log.info("Process year aggregate statistics for %i", target_phenoyear)
    statistics.process_1y_aggregate_statistics(target_phenoyear)

    log.info(
        "Setting current phenoyear from %i to %i", source_phenoyear, target_phenoyear
    )
    d.update_phenoyear(target_phenoyear)


def get_stale_individuals(year: int) -> list[str]:
    """
    Remove all individuals in Firestore that have no observations for any
    sources or sensor data for the given phenoyear year.
    :param year: the phenoyear
    """
    stale_list = []
    for individual_doc in d.query_individuals("year", "==", year).stream():
        individual = individual_doc.to_dict()
        if not (d.has_observations(individual) or d.has_sensor(individual)):
            stale_list.append(individual_doc.id)
    return stale_list


def remove_stale_individuals(year: int = None):
    # split querying and deleting to avoid stream timeouts
    if not year:
        year = d.get_phenoyear() - 1
    log.info("Gather stale individuals for %i", year)
    stale_individuals = get_stale_individuals(year)

    log.info(
        "Remove %i stale individuals for %i",
        len(stale_individuals),
        year,
    )
    for individual_id in stale_individuals:
        log.debug("Remove individual %s", individual_id)
        d.delete_individual(individual_id)
