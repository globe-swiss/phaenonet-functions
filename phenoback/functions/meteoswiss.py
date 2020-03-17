from typing import Optional

from requests import get
from hashlib import md5
import csv
import io
from datetime import datetime
from phenoback.gcloud.utils import *


def process_stations():
    response = get(
        'https://data.geo.admin.ch/ch.meteoschweiz.messnetz-phaenologie/ch.meteoschweiz.messnetz-phaenologie_en.csv')
    if response.ok:
        if _load_hash('stations') != _get_hash(response.text):
            reader = csv.DictReader(io.StringIO(response.text), delimiter=';')
            stations = _get_individuals_dict(reader)
            print('DEBUG: %i stations fetched in %s' % (len(stations), response.elapsed))
            write_batch('individuals', 'id', stations)
            _set_hash('stations', response.text)
        else:
            print('DEBUG: Station file did not change.')
    else:
        print('ERROR: Could not fetch station data (%s)' % response.status_code)


def _get_individuals_dict(stations: csv.DictReader):
    return [{
        'id': '%i_%s' % (datetime.now().year, station['Abbr.']),
        'altitude': int(station['Station height m. a. sea level']),
        'geopos': {'lat': float(station['Latitude']), 'lng': float(station['Longitude'])},
        'individual': station['Abbr.'],
        'name': station['Station'],
        'source': 'meteoswiss',
        'user': 'meteoswiss',
        'year': datetime.now().year,
    } for station in stations if len(station['Abbr.']) == 3]


def process_observations():
    response = get('https://data.geo.admin.ch/ch.meteoschweiz.klima/phaenologie/phaeno_current.csv')
    if response.ok:
        new_hash = _get_hash(response.text)
        old_hash = _load_hash('observations')
        if old_hash != new_hash:
            reader = csv.DictReader(io.StringIO(response.text), delimiter=';')
            observations = _get_observations_dict(reader)
            print('DEBUG: %i observations fetched in %s' % (len(observations), response.elapsed))
            write_batch('observations', 'id', observations)
            _set_hash('observations', response.text)
        else:
            print('DEBUG: Observations file did not change.')
    else:
        print('ERROR: Could not fetch observation data (%s)' % response.status_code)


def _get_observations_dict(observations: csv.DictReader):
    mapping = get_document('definitions/meteoswiss_mapping')
    return [{
        'id': '%s_%s_%s_%s' % (observation['nat_abbr'],
                               observation['reference_year'],
                               mapping[observation['param_id']]['species'],
                               mapping[observation['param_id']]['phenophase']),
        'date': datetime.strptime(observation['value'], '%Y%m%d'),
        'individual_id': '%s_%s' % (observation['reference_year'], observation['nat_abbr']),
        'individual': observation['nat_abbr'],
        'source': 'meteoswiss',
        'year': int(observation['reference_year']),
        'species': mapping[observation['param_id']]['species'],
        'phenophase': mapping[observation['param_id']]['phenophase']
    } for observation in observations]


def _set_hash(key: str, data: str):
    write_document('definitions', 'meteoswiss_import', {'hash_%s' % key: _get_hash(data)}, merge=True)


def _load_hash(key: str) -> Optional[str]:
    doc = get_document('definitions/meteoswiss_import')
    return doc.get('hash_%s' % key) if doc else None


def _get_hash(data) -> str:
    return md5(data.encode()).hexdigest()
