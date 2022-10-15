import logging
from datetime import datetime
from typing import Optional

import google

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.functions.iot.dragino import DraginoDecoder

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

COLLECTION = "sensors"


def process_dragino(data: dict) -> None:
    decoder = DraginoDecoder(data)
    decoder.decode()
    year = d.get_phenoyear()
    individual_id = get_individual_id(year, decoder.devuei)
    if individual_id:
        log.info("process sensor data for %s (%s)", individual_id, decoder.devuei)
        update(decoder.decoded_payload, year, individual_id)
    else:
        log.error("No individual found for %s in %i", decoder.devuei, year)


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
    today = datetime.now().strftime("%Y-%m-%d")
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
