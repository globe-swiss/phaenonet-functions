import logging
from functools import lru_cache
from typing import Dict, List

from phenoback.utils import firestore as f
from phenoback.utils import tasks

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

QUEUE_NAME = "mapupdates"
FUNCTION_NAME = "process_individual_map"


@lru_cache
def client() -> tasks.HTTPClient:
    return tasks.HTTPClient(QUEUE_NAME, FUNCTION_NAME)


def enqueue_change(
    individual_id: str,
    species: str,
    station_species: List[str],
    individual_type: str,
    last_phenophase: str,
    geopos: Dict[str, float],
    source: str,
    year: int,
    updated_fields: List[str],
) -> None:
    if _should_update(updated_fields):
        values = {
            individual_id: {
                "t": individual_type,
                "g": geopos,
                "so": source,
            }
        }
        if last_phenophase:
            values[individual_id]["p"] = last_phenophase
        if species:
            values[individual_id]["sp"] = species
        if station_species:
            values[individual_id]["ss"] = station_species

        payload = {}
        payload["year"] = year
        payload["values"] = values
        client().send(payload)
        log.info(
            "enqueue task for change on %s: fields=%s",
            individual_id,
            updated_fields,
        )
    else:
        log.debug(
            "nothing to do for change on %s: fields=%s",
            individual_id,
            updated_fields,
        )


def process_change(payload: Dict) -> None:
    f.write_document(
        "maps", str(payload["year"]), {"data": payload["values"]}, merge=True
    )
    log.info("update map for %s", str(payload["values"].keys()))


def _should_update(updated_fields: List[str]) -> bool:
    return any(
        elem
        in [
            "geopos.lat",
            "geopos.lng",
            "station_species",
            "last_phenophase",
            "source",
        ]
        for elem in updated_fields
    )


def delete(year: int, individual_id: str) -> None:
    f.update_document("maps", str(year), {f"data.{individual_id}": f.DELETE_FIELD})
