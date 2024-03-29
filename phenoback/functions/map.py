import logging
from functools import lru_cache
from http import HTTPStatus
from typing import Dict, List

from flask import Request, Response

from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g
from phenoback.utils import tasks

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

QUEUE_NAME = "mapupdates"
FUNCTION_NAME = "http_individuals_write__map"

DELETE_TOKEN = "__DELETE__"  # nosec


def main_enqueue(data, context):
    if not g.is_delete_event(data):
        enqueue_change(
            g.get_document_id(context),
            g.get_fields_updated(data),
            g.get_field(data, "species", expected=False),
            g.get_field(data, "station_species", expected=False),
            g.get_field(data, "type"),
            g.get_field(data, "last_phenophase", expected=False),
            g.get_field(data, "geopos"),
            g.get_field(data, "source"),
            g.get_field(data, "year"),
            g.get_field(data, "deveui", expected=False),
            g.is_create_event(data),
        )
    else:
        delete(g.get_field(data, "year", old_value=True), g.get_document_id(context))


def main_process(request: Request):
    process_change(request.get_json(silent=True))
    return Response("ok", HTTPStatus.OK)


@lru_cache
def client() -> tasks.GCFClient:
    return tasks.GCFClient(QUEUE_NAME, FUNCTION_NAME)


def enqueue_change(
    individual_id: str,
    updated_fields: List[str],
    species: str,
    station_species: List[str],
    individual_type: str,
    last_phenophase: str,
    geopos: Dict[str, float],
    source: str,
    year: int,
    deveui: str,
    is_create_event: bool,
) -> None:
    if _should_update(updated_fields, is_create_event):
        values = {
            individual_id: {
                "t": individual_type,
                "g": geopos,
                "so": source,
            }
        }
        values[individual_id]["p"] = (
            last_phenophase if last_phenophase else DELETE_TOKEN
        )
        values[individual_id]["sp"] = species if species else DELETE_TOKEN
        values[individual_id]["ss"] = (
            station_species if station_species else DELETE_TOKEN
        )
        values[individual_id]["hs"] = True if deveui else DELETE_TOKEN

        payload = {"year": year, "values": values}
        client().send(payload)
        log.info(
            "enqueue task for change on %s: fields=%s, created=%s",
            individual_id,
            updated_fields,
            is_create_event,
        )
    else:
        log.debug(
            "nothing to do for change on %s: fields=%s, created=%s",
            individual_id,
            updated_fields,
            is_create_event,
        )


def process_change(payload: dict) -> None:
    replace_delete_tokens(payload)
    f.write_document(
        "maps", str(payload["year"]), {"data": payload["values"]}, merge=True
    )
    log.info("update map for %s", str(payload["values"].keys()))


def replace_delete_tokens(payload: dict) -> None:
    for individual_dict in payload["values"].values():
        for key, value in individual_dict.items():
            individual_dict[key] = f.DELETE_FIELD if value == DELETE_TOKEN else value


def _should_update(updated_fields: List[str], is_create_event: bool) -> bool:
    return is_create_event or any(
        elem
        in [
            "geopos.lat",
            "geopos.lng",
            "station_species",
            "last_phenophase",
            "source",
            "deveui",
            "type",
            "species",
            "reprocess",
        ]
        for elem in updated_fields
    )


def delete(year: int, individual_id: str) -> None:
    f.update_document("maps", str(year), {f"data.{individual_id}": f.DELETE_FIELD})


def init(year: int) -> None:
    f.write_document("maps", str(year), {"year": year, "data": {}})
