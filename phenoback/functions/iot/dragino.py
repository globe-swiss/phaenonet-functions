import logging
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from http import HTTPStatus

from flask import Request, Response

from phenoback.functions.iot.decoder import Decoder
from phenoback.utils import pubsub, tasks

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

TOPIC_ID = "iot_dragino"
DOWNLINK_QUEUE = "swisscom-iot"
DOWNLINK_URL = "https://proxy1.lpn.swisscom.ch/thingpark/lrc/rest/downlink"


def main(request: Request):
    if request.is_json and request.json:
        process_dragino(request.json)
    else:  # pragma: no cover
        log.error("No json headers set or payload is None")
        return Response("No json payload", HTTPStatus.BAD_REQUEST)
    return Response("ok", HTTPStatus.OK)


@lru_cache
def ps_client() -> pubsub.Publisher:
    return pubsub.Publisher(TOPIC_ID)  # pragma: no cover


@lru_cache
def task_client() -> tasks.HTTPClient:
    return tasks.HTTPClient(DOWNLINK_QUEUE, DOWNLINK_URL)  # pragma: no cover


def process_dragino(data: dict) -> None:
    decoder = DraginoDecoder(data)
    if decoder.is_uplink:
        decoder.decode()
        ps_client().send(
            decoder.data,
            {
                "DevEUI": decoder.devuei,
                "Time": decoder.time,
            },
        )
        log.info("Published sensor event for %s to %s", decoder.devuei, TOPIC_ID)
    else:
        log.debug("No uplink data, skip")


def set_uplink_frequency(deveui: str, interval: int, at: datetime | None = None):
    log.info("set uplink frequency to %is for %s at %s", interval, deveui, at)
    task_client().send(
        "",
        params={
            "DevEUI": deveui,
            "Payload": f"{16777216 + interval:{0}8x}",
            "FPort": 1,
        },
        at=at,
    )


class DraginoDecoder(Decoder):
    result = defaultdict(dict)

    def set(self, field: str, value: float, precision: int, unit: str):
        self.result[field]["value"] = round(value, precision)
        self.result[field]["unit"] = unit

    def decode_impl(self) -> dict:
        self.set("soilHumidity", self.get_value(0 * 8, 16) / 1000 * 50 / 3, 2, "%")
        self.set(
            "soilTemperature", (self.get_value(2 * 8, 16) / 1000 - 0.5) * 100, 1, "°C"
        )
        self.set("airHumidity", self.get_value(9 * 8, 16) / 10, 2, "%")
        self.set("airTemperature", self.get_value(7 * 8, 16, signed=True) / 10, 2, "°C")
        self.set("batteryVoltage", self.get_value(88, 8) / 10, 1, "V")
        return dict(self.result)
