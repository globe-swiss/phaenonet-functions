import logging
from typing import Optional
from datetime import datetime

from phenoback.gcloud.utils import get_document, write_document
import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

STATE_COLLECTION = 'analytics_state'
RESULT_COLLECTION = 'analytics_result'


def update_state(observation_id, observation_date, phase, source, year, species, altitude_grp=None) -> dict:
    log.debug('Update state: (observation_id: %s, observation_date: %s, phase: %s, source: %s, year: %i, '
              'species: %s, altitude_grp: %s)' % (observation_id, observation_date, phase, source, year, species,
                                                  altitude_grp))
    document_id = get_analytics_document_id(year, species, source, altitude_grp)
    state_document = get_document(STATE_COLLECTION, document_id)
    state = {}
    if state_document.get('state'):
        state = state_document.get('state')

    state.setdefault(phase, dict())[observation_id] = observation_date
    state_document = {'source': source, 'year': year, 'species': species, 'state': state}
    if altitude_grp:
        state_document['altitude_grp'] = altitude_grp
    write_document(STATE_COLLECTION, document_id, state_document, merge=True)
    return state[phase]


def update_result(state: dict, phase, source, year, species, altitude_grp=None) -> None:
    log.debug('Write results: (phase: %s, source: %s, year: %i, species: %s, altitude_grp: %s)'
              % (phase, source, year, species, altitude_grp))
    document_id = get_analytics_document_id(year, species, source, altitude_grp)
    state_list = (list(state.values()))
    values = {phase:
              {'min': np.min(state_list),
               'max': np.max(state_list),
               'median': np.quantile(state_list, 0.5, interpolation='nearest'),
               'quantile_25': np.quantile(state_list, 0.25, interpolation='nearest'),
               'quantile_75': np.quantile(state_list, 0.75, interpolation='nearest')
               }}
    result_document = {'source': source, 'year': year, 'species': species, 'values': values}
    if altitude_grp:
        result_document['altitude_grp'] = altitude_grp
        result_document['type'] = 'altitude'
    else:
        result_document['type'] = 'species'
    write_document(RESULT_COLLECTION, document_id, result_document, merge=True)


def update_data(observation_id: str, observation_date: datetime, year: int, species: str, phase: str, source: str,
                altitude_grp: str = None) -> None:
    state = update_state(observation_id, observation_date,
                         phase, source, year, species, altitude_grp)
    update_result(state, phase, source, year, species, altitude_grp)


def remove_data(observation_id: str, year: int, species: str, phase: str, source: str,
                altitude_grp: str = None) -> None:
    try:
        document_id = get_analytics_document_id(year, species, source, altitude_grp)
        state_document = get_document(STATE_COLLECTION, document_id)
        state = state_document['state']
        state[phase].pop(observation_id)
        write_document(STATE_COLLECTION, document_id, state_document, merge=True)

        update_result(state, phase, source, year, species, altitude_grp)
    except KeyError:
        log.error('Observation not found for removal: (observation_id: %s, source: %s, year: %i, species: %s, '
                  'phase: %s)' % (observation_id, source, year, species, phase))


def get_altitude_grp(individual_id: str) -> Optional[str]:
    altitude = get_document('individuals', individual_id).get('altitude', None)
    altitude_key = None
    if altitude is not None:
        if altitude < 500:
            altitude_key = 'alt1'
        elif altitude < 800:
            altitude_key = 'alt2'
        elif altitude < 1000:
            altitude_key = 'alt3'
        elif altitude < 1200:
            altitude_key = 'alt4'
        else:
            altitude_key = 'alt5'
    else:
        log.error('no altitude found for individual %s' % individual_id)
    return altitude_key


def get_analytics_document_id(year: int, species: str, source: str, altitude_grp: str = None) -> str:
    if altitude_grp:
        return '%s_%s_%s_%s' % (str(year), species, source, altitude_grp)
    else:
        return '%s_%s_%s' % (str(year), species, source)


def process_observation(observation_id: str, observation_date: datetime, individual_id: str,
                        source: str, year: int, species: str, phase: str):
    log.info('Process observation: (observation_id: %s, observation_date: %s, individual_id: %s, source: %s, '
             'year: %i, species: %s, phase: %s)' % (observation_id, observation_date, individual_id, source, year,
                                                    species, phase))
    update_data(observation_id=observation_id,
                observation_date=observation_date,
                year=year,
                species=species,
                phase=phase,
                source=source)
    update_data(observation_id=observation_id,
                observation_date=observation_date,
                year=year,
                species=species,
                phase=phase,
                source='all')

    altitude_key = get_altitude_grp(individual_id)
    if altitude_key:
        update_data(observation_id=observation_id,
                    observation_date=observation_date,
                    year=year,
                    species=species,
                    phase=phase,
                    source=source,
                    altitude_grp=altitude_key)
        update_data(observation_id=observation_id,
                    observation_date=observation_date,
                    year=year,
                    species=species,
                    phase=phase,
                    source='all',
                    altitude_grp=altitude_key)


def process_remove_observation(observation_id: str, individual_id: str, source: str,  year: int, species: str,
                               phase: str):
    log.info('Remove observation: (observation_id: %s,  individual_id: %s, source: %s, '
             'year: %i, species: %s, phase: %s)' % (observation_id, individual_id, source, year,
                                                    species, phase))
    remove_data(observation_id=observation_id,
                year=year,
                species=species,
                phase=phase,
                source=source)
    remove_data(observation_id=observation_id,
                year=year,
                species=species,
                phase=phase,
                source='all')

    altitude_key = get_altitude_grp(individual_id)
    if altitude_key:
        remove_data(observation_id=observation_id,
                    year=year,
                    species=species,
                    phase=phase,
                    source=source,
                    altitude_grp=altitude_key)
        remove_data(observation_id=observation_id,
                    year=year,
                    species=species,
                    phase=phase,
                    source='all',
                    altitude_grp=altitude_key)
