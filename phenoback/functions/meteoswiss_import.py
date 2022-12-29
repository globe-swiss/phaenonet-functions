import csv
import io
import logging
from datetime import datetime
from hashlib import md5
from typing import Dict, List, Optional

from requests import get

from phenoback.utils.data import get_phenoyear, update_individual
from phenoback.utils.firestore import (
    ArrayUnion,
    get_document,
    write_batch,
    write_document,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class ResourceNotFoundException(Exception):
    pass


def main(data, context):  # pylint: disable=unused-argument
    log.info("Import meteoswiss stations")
    process_stations()
    log.info("Import meteoswiss observations")
    process_observations()


def process_stations() -> bool:
    response = get(
        "https://data.geo.admin.ch/ch.meteoschweiz.messnetz-phaenologie/ch.meteoschweiz.messnetz-phaenologie_en.csv",
        timeout=60,
    )
    if response.ok:
        return process_stations_response(response.text, response.elapsed)
    else:
        msg = f"Could not fetch station data ({response.status_code})"
        log.error(msg)
        raise ResourceNotFoundException(msg)


def process_stations_response(response_text: str, response_elapsed: float) -> bool:
    phenoyear = get_phenoyear()
    csv_string = _clean_station_csv(response_text)
    if _load_hash("stations") != _get_hash(str(phenoyear) + csv_string):
        reader = csv.DictReader(io.StringIO(csv_string), delimiter=";")
        stations = _get_individuals_dicts(phenoyear, reader)
        log.info("Update %i stations fetched in %s", len(stations), response_elapsed)
        write_batch("individuals", "id", stations, merge=True)
        _set_hash(
            "stations", str(phenoyear) + csv_string
        )  # trigger re-import in new phenoyear
        return True
    else:
        log.info("Station file did not change.")
        return False


def _clean_station_csv(text):
    return text.split("\n\n")[0]


def _get_individuals_dicts(phenoyear: int, stations: csv.DictReader) -> List[Dict]:
    return [
        {
            "id": f"{phenoyear}_{station['Abbr.']}",
            "altitude": int(station["Station height m a. sea level"]),
            "geopos": {
                "lat": float(station["Latitude"]),
                "lng": float(station["Longitude"]),
            },
            "individual": station["Abbr."],
            "name": station["Station"],
            "source": "meteoswiss",
            "user": "meteoswiss",
            "type": "station",
            "year": phenoyear,
        }
        for station in stations
    ]


def process_observations() -> bool:
    response = get(
        "https://data.geo.admin.ch/ch.meteoschweiz.klima/phaenologie/phaeno_current.csv",
        timeout=60,
    )
    if response.ok:
        return process_observations_response(response.text, response.elapsed)
    else:
        msg = f"Could not fetch observation data ({response.status_code})"
        log.error(msg)
        raise ResourceNotFoundException(msg)


def process_observations_response(response_text: str, response_elapsed: float) -> bool:
    if _load_hash("observations") != _get_hash(response_text):
        reader = csv.DictReader(io.StringIO(response_text), delimiter=";")
        observations = _get_observations_dicts(reader)
        log.info(
            "Update %i observations fetched in %s",
            len(observations),
            response_elapsed,
        )
        # write observations
        write_batch("observations", "id", observations, merge=True)
        # update stations
        _update_station_species(_get_station_species(observations))
        _set_hash("observations", response_text)
        return True
    else:
        log.info("Observations file did not change.")
        return False


def _get_observations_dicts(observations: csv.DictReader) -> List[Dict]:
    mapping = get_document("definitions", "meteoswiss_mapping")
    return [
        {
            "id": f"{observation['nat_abbr']}_{observation['reference_year']}_{mapping[observation['param_id']]['species']}_{mapping[observation['param_id']]['phenophase']}",
            "user": "meteoswiss",
            "date": datetime.strptime(observation["value"], "%Y%m%d"),
            "individual_id": f"{observation['reference_year']}_{observation['nat_abbr']}",
            "individual": observation["nat_abbr"],
            "source": "meteoswiss",
            "year": int(observation["reference_year"]),
            "species": mapping[observation["param_id"]]["species"],
            "phenophase": mapping[observation["param_id"]]["phenophase"],
        }
        for observation in observations
        if observation["param_id"] in mapping
    ]


def _get_station_species(observations: List[dict]) -> Dict[str, Optional[List[str]]]:
    station_species: dict = {}
    for observation in observations:
        station_species.setdefault(observation["individual_id"], []).append(
            observation["species"]
        )
    return station_species


def _update_station_species(station_species: dict) -> None:
    for key in station_species.keys():
        data = {"station_species": ArrayUnion(station_species[key])}
        update_individual(key, data)


def _set_hash(key: str, data: str):
    hashed_data = _get_hash(data)
    write_document(
        "definitions", "meteoswiss_import", {f"hash_{key}": hashed_data}, merge=True
    )
    log.debug("set hash for %s to %s", key, hashed_data)


def _load_hash(key: str) -> Optional[str]:
    doc = get_document("definitions", "meteoswiss_import")
    loaded_hash = doc.get(f"hash_{key}") if doc else None
    log.debug("loaded hash for %s to %s", key, loaded_hash)
    return loaded_hash


def _get_hash(data: str) -> str:
    # pylint: disable=unexpected-keyword-arg
    return md5(data.encode(), usedforsecurity=False).hexdigest()
