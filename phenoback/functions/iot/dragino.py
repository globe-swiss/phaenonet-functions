import logging
from collections import defaultdict
from functools import lru_cache

from phenoback.functions.iot.decoder import Decoder
from phenoback.utils import pubsub

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

TOPIC_ID = "iot_dragino"


@lru_cache
def client() -> pubsub.Publisher:
    return pubsub.Publisher(TOPIC_ID)


def process_dragino(data: dict) -> None:
    decoder = DraginoDecoder(data)
    if decoder.is_uplink:
        decoder.decode()
        client().send(
            decoder.data,
            {
                "DevEUI": decoder.devuei,
                "Time": decoder.time,
            },
        )
        log.info("Published sensor event for %s to %s", decoder.devuei, TOPIC_ID)
    else:
        log.debug("No uplink data, skip")


class DraginoDecoder(Decoder):
    result = defaultdict(lambda: {})

    def set(self, field: str, value: float, precision: int, unit: str):
        self.result[field]["value"] = round(value, precision)
        self.result[field]["unit"] = unit

    def decode_impl(self) -> dict:
        self.set("soilHumidity", self.get_value(0 * 8, 16) / 1000 * 50 / 3, 2, "%")
        self.set(
            "soilTemperature", (self.get_value(2 * 8, 16) / 1000 - 0.5) * 100, 1, "°C"
        )
        self.set("airHumidity", self.get_value(9 * 8, 16) / 10, 2, "%")
        self.set("airTemperature", self.get_value(7 * 8, 16) / 10, 2, "°C")
        self.set("batteryVoltage", self.get_value(88, 8) / 10, 1, "V")
        return dict(self.result)
