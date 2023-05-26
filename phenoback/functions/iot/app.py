import datetime
import logging
from http import HTTPStatus
from typing import Optional
from zoneinfo import ZoneInfo

import google
from flask import Request, Response

import phenoback.utils.data as d
import phenoback.utils.firestore as f
import phenoback.utils.gcloud as g
from phenoback.functions.iot import dragino
from phenoback.functions.iot.dragino import DraginoDecoder

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

COLLECTION = "sensors"


def main(event, context):  # pylint: disable=unused-argument
    json_data = g.get_data(event)
    process_dragino(json_data)


def main_set_sensor(request: Request):
    msg = "ok"
    status = HTTPStatus.OK
    individual = request.json.get("individual")
    deveui = request.json.get("deveui")
    year = request.json.get("year")

    if request.is_json and deveui and individual and year:
        if not set_sensor(individual, year, deveui):
            msg = f"individual {individual} not found in {year}"
            status = HTTPStatus.NOT_FOUND
            log.error(msg)
    else:
        msg = f"Invalid request (json={request.is_json}, individual={individual}, year={year}, deveui={deveui}"
        status = HTTPStatus.BAD_REQUEST
        log.error(msg)
    return Response(msg, status)


def process_dragino(data: dict) -> None:
    decoder = DraginoDecoder(data)
    decoder.decode()
    year = d.get_phenoyear()
    individual_id = get_individual_id(year, decoder.devuei)
    if individual_id:
        log.info("process sensor data for %s (%s)", individual_id, decoder.devuei)
        update(decoder.decoded_payload, year, individual_id)
    else:
        log.warning("No individual found for %s in %i", decoder.devuei, year)


def get_individual_id(year: int, deveui: str) -> Optional[str]:
    individual_id = None
    for doc in (
        d.query_individuals("deveui", "==", deveui)
        .where("year", "==", year)
        .limit(1)
        .stream()
    ):
        individual_id = doc.id
    return individual_id


def update(data: dict, year: int, individual_id: str):
    soil_humidity = data["soilHumidity"]["value"]
    soil_temperature = data["soilTemperature"]["value"]
    air_humidity = data["airHumidity"]["value"]
    air_temperature = data["airTemperature"]["value"]

    update_history(
        year,
        individual_id,
        soil_humidity,
        soil_temperature,
        air_humidity,
        air_temperature,
    )
    update_individual(
        individual_id,
        soil_humidity,
        soil_temperature,
        air_humidity,
        air_temperature,
    )


def update_history(
    year: int,
    individual_id: str,
    soil_humidity: float,
    soil_temperature: float,
    air_humidity: float,
    air_temperature: float,
):
    today = d.localdate()
    data_today = {}
    data_today[f"data.{today}.shs"] = f.Increment(soil_humidity)
    data_today[f"data.{today}.sts"] = f.Increment(soil_temperature)
    data_today[f"data.{today}.ahs"] = f.Increment(air_humidity)
    data_today[f"data.{today}.ats"] = f.Increment(air_temperature)
    data_today[f"data.{today}.n"] = f.Increment(1)

    try:
        f.update_document(COLLECTION, individual_id, data_today)
    except google.api_core.exceptions.NotFound:
        # create document and try again
        f.write_document(COLLECTION, individual_id, {"year": year})
        f.update_document(COLLECTION, individual_id, data_today)


def update_individual(
    individual_id: str,
    soil_humidity: float,
    soil_temperature: float,
    air_humidity: float,
    air_temperature: float,
):
    d.update_individual(
        individual_id,
        {
            "sensor": {
                "sh": soil_humidity,
                "st": soil_temperature,
                "ah": air_humidity,
                "at": air_temperature,
                "ts": f.SERVER_TIMESTAMP,
            }
        },
    )


def set_sensor(individual: str, year: int, deveui: str) -> bool:
    individual_id = None
    for doc in (
        f.query_collection("individuals", "year", "==", year)
        .where("individual", "==", individual)
        .stream()
    ):
        individual_id = doc.id
    remove_sensor(deveui, year)
    try:
        d.update_individual(individual_id, {"deveui": deveui})
        log.info(
            "set sensor %s on individual %s in %i (id=%s)",
            deveui,
            individual_id,
            year,
            individual_id,
        )
        increase_uplink_frequency(deveui)
    except google.api_core.exceptions.NotFound:
        log.warning(
            "individual %s not found in %i setting sensor %s (id=%s)",
            individual_id,
            year,
            deveui,
            individual_id,
        )
        return False
    return True


def remove_sensor(deveui: str, year: int) -> bool:
    individual_id = get_individual_id(year, deveui)
    if individual_id:
        log.info("remove sensor %s on individual %s", deveui, individual_id)
        d.update_individual(
            individual_id,
            {
                "deveui": f.DELETE_FIELD,
                "sensor": {},
            },
        )
        return True
    return False


def clear_sensors(year: int) -> int:
    """Clears all sensor data on individuals"""
    individual_ids = [
        doc.id
        for doc in f.collection("individuals").order_by("deveui").stream()
        if doc.to_dict()["year"] == year
    ]
    for individual_id in individual_ids:
        d.update_individual(
            individual_id,
            {
                "sensor": {},
            },
        )
    return len(individual_ids)


def increase_uplink_frequency(deveui: str):
    dragino.set_uplink_frequency(deveui, 600)
    tomorrow = d.localdate() + datetime.timedelta(days=1)
    dragino.set_uplink_frequency(
        deveui,
        3600,
        datetime.datetime(
            tomorrow.year,
            tomorrow.month,
            tomorrow.day,
            tzinfo=ZoneInfo("Europe/Zurich"),
        ),
    )
