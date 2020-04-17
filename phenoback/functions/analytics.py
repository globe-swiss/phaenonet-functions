import logging
from typing import Optional
from datetime import datetime

from phenoback.gcloud.utils import firestore_client
import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def _process_state(ref, observation_id, observation_date, phase, source, year, species, altitude_grp=None) -> dict:
    log.debug('DEBUG: Process State: (observation_id: %s, observation_date: %s, phase: %s, source: %s, year: %i, '
              'species: %s, altitude_grp: %s)' % (observation_id, observation_date, phase, source, year, species,
                                                  altitude_grp))
    snapshot = ref.get()
    state = {}
    if snapshot.get('state'):
        state = snapshot.get('state')

    state.setdefault(phase, dict())[observation_id] = observation_date
    data = {'source': source, 'year': year, 'species': species, 'state': state}
    if altitude_grp:
        data['altitude_grp'] = altitude_grp
    ref.set(data, merge=True)
    return state[phase]


def _process_results(ref, state: dict, phase, source, year, species, altitude_grp=None) -> None:
    log.debug('Process Results: (phase: %s, source: %s, year: %i, species: %s, altitude_grp: %s)'
              % (phase, source, year, species, altitude_grp))
    state_list = (list(state.values()))
    values = {phase:
              {'min': np.min(state_list),
               'max': np.max(state_list),
               'median': np.quantile(state_list, 0.5, interpolation='nearest'),
               'quantile_25': np.quantile(state_list, 0.25, interpolation='nearest'),
               'quantile_75': np.quantile(state_list, 0.75, interpolation='nearest')
               }}
    data = {'source': source, 'year': year, 'species': species, 'values': values}
    if altitude_grp:
        data['altitude_grp'] = altitude_grp
        data['type'] = 'altitude'
    else:
        data['type'] = 'species'

    ref.set(data, merge=True)


def _update_dataset(observation_id: str, observation_date: datetime, year: int, species: str, phase: str, source: str,
                    altitude_grp: str = None):
    if altitude_grp:
        doc_key = '%s_%s_%s_%s' % (str(year), species, source, altitude_grp)
    else:
        doc_key = '%s_%s_%s' % (str(year), species, source)

    log.debug('Process state and result for %s' % doc_key)
    state_ref = firestore_client().collection('analytics_state').document(doc_key)
    state = _process_state(state_ref, observation_id, observation_date,
                           phase, source, year, species, altitude_grp)

    result_ref = firestore_client().collection('analytics_result').document(doc_key)
    _process_results(result_ref, state, phase, source, year, species, altitude_grp)


def _get_altitude_grp(individual_id: str) -> Optional[str]:
    altitude = firestore_client().collection('individuals').document(individual_id).get().to_dict().get('altitude', None)
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


def process_observation(observation_id: str, observation_date: datetime, individual_id: str,
                        source: str, year: int, species: str, phase: str):
    log.info('Process observation: (observation_id: %s, observation_date: %s, individual_id: %s, source: %s, '
             'year: %i, species: %s, phase: %s)' % (observation_id, observation_date, individual_id, source, year,
                                                    species, phase))
    _update_dataset(observation_id=observation_id,
                    observation_date=observation_date,
                    year=year,
                    species=species,
                    phase=phase,
                    source=source)
    _update_dataset(observation_id=observation_id,
                    observation_date=observation_date,
                    year=year,
                    species=species,
                    phase=phase,
                    source='all')

    altitude_key = _get_altitude_grp(individual_id)
    if altitude_key:
        _update_dataset(observation_id=observation_id,
                        observation_date=observation_date,
                        year=year,
                        species=species,
                        phase=phase,
                        source=source,
                        altitude_grp=altitude_key)
        _update_dataset(observation_id=observation_id,
                        observation_date=observation_date,
                        year=year,
                        species=species,
                        phase=phase,
                        source='all',
                        altitude_grp=altitude_key)


def process_remove_observation(observation_id):
    raise NotImplementedError('removing of observations not implemented (id=%s)' % observation_id)
