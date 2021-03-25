import logging

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


def rollover_individuals(source_phenoyear, target_phenoyear, individual=None):
    """
    Copy individuals to a new phenoyear, removing all fields that are specific for the phenoyear.
    :param source_phenoyear:
    :param target_phenoyear:
    :return:
    """
    log.info("Rollover individuals of %i to %i", source_phenoyear, target_phenoyear)
    new_individuals = []
    query = query_individuals("year", "==", source_phenoyear).where(
        "source", "==", "globe"
    )
    if individual:
        query = query.where("individual", "==", individual)
    for individual_doc in query.stream():
        individual = individual_doc.to_dict()
        individual["id"] = "%i_%s" % (target_phenoyear, individual["individual"])
        individual["year"] = target_phenoyear
        for key in ["last_phenophase", "last_observation_date", "created", "modified"]:
            individual.pop(key, None)
        new_individuals.append(individual)
        log.debug("rolling over individual %s", individual)
    log.info(
        "Creating %i new individuals in %i", len(new_individuals), target_phenoyear
    )
    write_individuals(new_individuals, "id")


def remove_stale_individuals(year: int):
    """
    Remove all individuals in Firestore that have no observations for all
    sources (globe and meteoswiss) for the given phenoyear year.
    :param year: the phenoyear
    """
    log.info("Remove stale individuals for %i", year)
    del_list = []
    # split querying and deleting to avoid stream timeouts
    for individual_doc in query_individuals("year", "==", year).stream():
        if not has_observations(individual_doc.to_dict()):
            del_list.append(individual_doc.id)
    for individual_id in del_list:
        log.debug("Remove individual %s", individual_id)
        delete_individual(individual_id)
    log.info("Removed %i stale individuals for %i", len(del_list), year)


def rollover():
    phenoyear = get_phenoyear()
    next_year = phenoyear + 1
    rollover_individuals(phenoyear, next_year)
    remove_stale_individuals(phenoyear)
    log.info("Setting current year to %i", next_year)
    update_phenoyear(next_year)
