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


def process_stations() -> bool:
    response = get(
        "https://data.geo.admin.ch/ch.meteoschweiz.messnetz-phaenologie/ch.meteoschweiz.messnetz-phaenologie_en.csv"
    )
    if response.ok:
        csv_string = _clean_station_csv(response.text)
        if _load_hash("stations") != _get_hash(csv_string):
            reader = csv.DictReader(io.StringIO(csv_string), delimiter=";")
            stations = _get_individuals_dicts(reader)
            log.info(
                "Update %i stations fetched in %s", len(stations), response.elapsed
            )
            write_batch("individuals", "id", stations, merge=True)
            _set_hash("stations", csv_string)
            return True
        else:
            log.info("Station file did not change.")
            return False
    else:
        log.error("Could not fetch station data (%s)", response.status_code)
        raise ResourceNotFoundException(
            "Could not fetch station data (%s)" % response.status_code
        )


def _clean_station_csv(text):
    return text.split("\n\n")[0]


def _get_individuals_dicts(stations: csv.DictReader) -> List[Dict]:
    phenoyear = get_phenoyear()
    return [
        {
            "id": "%i_%s" % (phenoyear, station["Abbr."]),
            "altitude": int(station["Station height m. a. sea level"]),
            "geopos": {
                "lat": float(station["Latitude"]),
                "lng": float(station["Longitude"]),
            },
            "individual": station["Abbr."],
            "name": station["Station"],
            "source": "meteoswiss",
            "user": "meteoswiss",
            "year": phenoyear,
        }
        for station in stations
    ]


def process_observations() -> bool:
    response = get(
        "https://data.geo.admin.ch/ch.meteoschweiz.klima/phaenologie/phaeno_current.csv"
    )
    if response.ok:
        new_hash = _get_hash(response.text)
        old_hash = _load_hash("observations")
        if old_hash != new_hash:
            reader = csv.DictReader(io.StringIO(response.text), delimiter=";")
            observations = _get_observations_dicts(reader)
            log.info(
                "Update %i observations fetched in %s",
                len(observations),
                response.elapsed,
            )
            # write observations
            write_batch("observations", "id", observations, merge=True)
            # update stations
            _update_station_species(_get_station_species(observations))
            _set_hash("observations", response.text)
            return True
        else:
            log.info("Observations file did not change.")
            return False
    else:
        log.error("Could not fetch observation data (%s)", response.status_code)
        raise ResourceNotFoundException(
            "Could not fetch observation data (%s)" % response.status_code
        )


def _get_observations_dicts(observations: csv.DictReader) -> List[Dict]:
    mapping = get_document("definitions", "meteoswiss_mapping")
    return [
        {
            "id": "%s_%s_%s_%s"
            % (
                observation["nat_abbr"],
                observation["reference_year"],
                mapping[observation["param_id"]]["species"],
                mapping[observation["param_id"]]["phenophase"],
            ),
            "user": "meteoswiss",
            "date": datetime.strptime(observation["value"], "%Y%m%d"),
            "individual_id": "%s_%s"
            % (observation["reference_year"], observation["nat_abbr"]),
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
        "definitions", "meteoswiss_import", {"hash_%s" % key: hashed_data}, merge=True
    )
    log.debug("set hash for %s to %s", key, hashed_data)


def _load_hash(key: str) -> Optional[str]:
    doc = get_document("definitions", "meteoswiss_import")
    loaded_hash = doc.get("hash_%s" % key) if doc else None
    log.debug("loaded hash for %s to %s", key, loaded_hash)
    return loaded_hash


def _get_hash(data) -> str:
    return md5(data.encode()).hexdigest()  # nosec (B303)
