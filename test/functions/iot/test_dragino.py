from unittest.mock import ANY

import pytest

from phenoback.functions.iot import dragino

SAMPLE_PAYLOAD = {"DevEUI_uplink": {"payload_hex": "01b4034001f30800fc01b821"}}
DECODED_PAYLOAD = {
    "soilHumidity": {"value": 7.27, "unit": "%"},
    "soilTemperature": {"value": 33.2, "unit": "°C"},
    "airHumidity": {"value": 44.0, "unit": "%"},
    "airTemperature": {"value": 25.2, "unit": "°C"},
    "batteryVoltage": {"value": 3.3, "unit": "V"},
}


@pytest.fixture(autouse=True)
def client(mocker):
    return mocker.patch("phenoback.functions.iot.dragino.client").return_value


def test_process(client):
    dragino.process_dragino(SAMPLE_PAYLOAD)
    SAMPLE_PAYLOAD["DevEUI_uplink"]["decoded_payload"] = DECODED_PAYLOAD

    client.send.assert_called_with(SAMPLE_PAYLOAD, ANY)


def test_process__no_uplink(client):
    dragino.process_dragino({})

    client.send.assert_not_called()


def test_decode_impl():
    decoder = dragino.DraginoDecoder(SAMPLE_PAYLOAD)
    decoder.decode()
    assert decoder.decoded_payload == DECODED_PAYLOAD
