from typing import List, Optional

import phenoback
from firebase_admin import firestore
from google.cloud.firestore_v1.client import Client
import numpy as np
from datetime import datetime

_db = None


def get_client() -> Client:
    global _db
    if not _db:
        _db = firestore.client()
    return _db


def _process_state(ref, observation_id, observation_date, phase, source, year, species, altitude_grp=None) -> dict:
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
    ref.set(data, merge=True)


def _update_dataset(observation_id: str, observation_date: datetime,
                    year: int, species: str, phase: str, source: str, altitude_grp: str = None):
    if altitude_grp:
        doc_key = '%s_%s_%s_%s' % (str(year), species, source, altitude_grp)
    else:
        doc_key = '%s_%s_%s' % (str(year), species, source)
    # process state by species
    state_ref = get_client().collection('analytics_state').document(doc_key)
    state = _process_state(state_ref, observation_id, observation_date,
                           phase, source, year, species, altitude_grp)

    # process analytic results
    result_ref = get_client().collection('analytics_result').document(doc_key)
    _process_results(result_ref, state, phase, source, year, species, altitude_grp)


def _get_altitude_grp(individual_id: str) -> Optional[str]:
    altitude = get_client().collection('individuals').document(individual_id).get().to_dict().get('altitude', None)
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
        print('Error: no altitude found for individual %s' % individual_id)
    return altitude_key


def process_observation(observation_id: str, observation_date: datetime, individual_id: str,
                        source: str, year: int, species: str, phase: str):
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


def remove_observation(observation_id):
    print("WARN: removing of observations not implemented")


# process_observation('1000_2016_HS_BLA', datetime.now(), '2019_1000', 'globe', 2016, 'HS', 'BLA')


