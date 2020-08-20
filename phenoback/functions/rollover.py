import logging

from phenoback.utils.data import query_individuals, write_individuals, has_observations, delete_individual, \
    get_phenoyear, update_phenoyear, write_individual

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def rollover_individuals(old_year, new_year):
    log.info("Rollover individuals of %i to %i" % (old_year, new_year))
    new_individuals = []
    for individual_doc in query_individuals('year', '==', old_year).where('source', '==', 'globe').stream():
        individual = individual_doc.to_dict()
        individual['id'] = '%i_%s' % (new_year, individual['individual'])
        individual['year'] = new_year
        for key in ['last_phenophase', 'last_observation_date', 'created', 'modified']:
            individual.pop(key, None)
        new_individuals.append(individual)
    log.debug("Creating %i new individuals")
    write_individuals(new_individuals, 'id')


def remove_stale_individuals(year: int):
    log.info("Remove stale individuals for %i" % year)
    del_cnt = 0
    for individual_doc in query_individuals('year', '==', year).stream():
        if has_observations(individual_doc.id):
            log.debug('Remove individual %s' % individual_doc.id)
            delete_individual(individual_doc.id)
            del_cnt += 1
    log.info("Removed %i stale individuals for %i" % (del_cnt, year))


def rollover():
    phenoyear = get_phenoyear()
    next_year = phenoyear + 1
    rollover_individuals(phenoyear, next_year)
    remove_stale_individuals(phenoyear)
    log.info('Set current year to %i' % next_year)
    update_phenoyear(next_year)
