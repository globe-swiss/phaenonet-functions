import pytest
from requests.models import Response

from phenoback.functions.iot import dragino, permarobotics


@pytest.fixture
def raw_data():
    return {
        "DevEUI_uplink": {
            "DevEUI": "cb773133e929f8a7",
            "payload_hex": "01620205000108000503e824",
            "LrrRSSI": -107,
            "FCntUp": 32,
            "Time": "2022-12-14T18:15:28.409+01:00",
            "FPort": 2,
        }
    }


@pytest.fixture
def decoded_payload():
    return {
        "airHumidity": {"value": 100, "unit": "%"},
        "airTemperature": {"value": 0.5, "unit": "°C"},
        "soilTemperature": {"unit": "°C", "value": 1.7},
        "soilHumidity": {"unit": "%", "value": 5.9},
        "batteryVoltage": {"unit": "V", "value": 3.6},
    }


@pytest.fixture
def data(raw_data, decoded_payload):
    raw_data["DevEUI_uplink"]["decoded_payload"] = decoded_payload
    return raw_data


def test_assert_compatible_decoder(raw_data, decoded_payload):
    decoder = dragino.DraginoDecoder(raw_data)
    decoder.decode()
    assert decoder.decoded_payload == decoded_payload


def test_send_permarobotics(mocker, data):
    response = Response()
    response.status_code = 200
    request_mock = mocker.patch("requests.post", return_value=response)
    assert permarobotics.send_permarobotics(data)
    args = request_mock.call_args[1]

    assert (
        args["url"]
        == "https://europe-west3-permarobotics.cloudfunctions.net/saveSensorData"
    )
    assert args["timeout"] > 0
    assert args["json"] is not None


def test_send_permarobotics__payload_format(mocker, data):
    response = Response()
    response.status_code = 200
    request_mock = mocker.patch("requests.post", return_value=response)

    assert permarobotics.send_permarobotics(data)
    call_json = request_mock.call_args[1]["json"]

    assert call_json == {
        "end_device_ids": {"dev_eui": "cb773133e929f8a7"},
        "uplink_message": {
            "received_at": "2022-12-14T18:15:28.409+01:00",
            "rx_metadata": [{"rssi": -107}],
            "f_port": 2,
            "f_cnt": 32,
            "frm_payload": "01620205000108000503e824",
            "decoded_payload": {
                "airHumidity": {"value": 100, "unit": "%"},
                "airTemperature": {"value": 0.5, "unit": "°C"},
                "soilTemperature": {"unit": "°C", "value": 1.7},
                "soilHumidity": {"unit": "%", "value": 5.9},
                "batteryVoltage": {"unit": "V", "value": 3.6},
            },
        },
    }


def test_send_permarobotics__error(mocker, caperrors, data):
    response = Response()
    response.status_code = 500
    response._content = str.encode("some error")  # pylint: disable=protected-access
    mocker.patch("requests.post", return_value=response)
    assert not permarobotics.send_permarobotics(data)
    assert len(caperrors.records) == 1
