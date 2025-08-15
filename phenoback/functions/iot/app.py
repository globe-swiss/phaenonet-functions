import logging

import google.api_core.exceptions

import phenoback.utils.data as d
import phenoback.utils.firestore as f
import phenoback.utils.gcloud as g
from phenoback.functions.iot import dragino
from phenoback.functions.iot.dragino import DraginoDecoder

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

COLLECTION = "sensors"


def main(data, context):  # pylint: disable=unused-argument
    process_dragino(data)


def main_individual_updated(data, context):
    if g.is_field_updated(data, "deveui"):
        log.debug("DevEUI updated")
        individual_id = g.get_document_id(context)
        if g.get_field(data, "deveui", expected=False):
            individual = g.get_field(data, "individual")
            deveui = g.get_field(data, "deveui")
            sensor_set(individual_id, str(individual), str(deveui))
        else:
            remove_sensor(individual_id)


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


def get_individual_id(year: int, deveui: str) -> str | None:
    individual_id = None
    for doc in (
        d.query_individuals("deveui", "==", deveui)
        .where(filter=f.FieldFilter("year", "==", year))
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


def valid_temperature(temperature):
    return -50 <= temperature <= 50


def valid_humidity(humidity):
    return 0 <= humidity <= 100


# pylint: disable=too-many-positional-arguments
def update_history(
    year: int,
    individual_id: str,
    soil_humidity: float,
    soil_temperature: float,
    air_humidity: float,
    air_temperature: float,
):
    if (
        valid_humidity(air_humidity)
        and valid_humidity(soil_humidity)
        and valid_temperature(air_temperature)
        and valid_temperature(soil_temperature)
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
    else:
        log.error(
            "Invalid sensor data for %s (air_temperature=%i, soil_temperature=%i, air_humidity=%i, soil_humidity=%i)",
            individual_id,
            air_temperature,
            soil_temperature,
            air_humidity,
            soil_humidity,
        )


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


def sensor_set(individual_id: str, individual: str, deveui: str) -> None:
    """Called after a sensor was set in Firebase."""
    log.debug("sensor set: %s -> %s", individual, deveui)
    for doc in d.query_individuals("deveui", "==", deveui).stream():
        i = doc.to_dict()
        if doc.id != individual_id and i.get("deveui"):
            remove_sensor(doc.id)
    dragino.set_uplink_frequency(deveui, 3600)


def remove_sensor(individual_id) -> None:
    log.info("remove sensor from individual_id %s", individual_id)
    d.update_individual(
        individual_id,
        {
            "deveui": f.DELETE_FIELD,
            "sensor": {},
        },
    )


def clear_sensors(year: int) -> int:
    """Clears all sensor data on individuals"""
    log.info("clear all sensors for %i", year)
    individual_ids = [
        doc.id
        for doc in f.collection("individuals").order_by("deveui").stream()
        if doc.to_dict()["year"] == year
    ]
    for individual_id in individual_ids:
        remove_sensor(individual_id)
    return len(individual_ids)
