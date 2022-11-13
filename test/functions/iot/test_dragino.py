from datetime import datetime
from test.functions.iot.sample_data import DraginoData as dd
from unittest.mock import ANY

import pytest

from phenoback.functions.iot import dragino


@pytest.fixture(autouse=True)
def ps_client(mocker):
    return mocker.patch("phenoback.functions.iot.dragino.ps_client").return_value


@pytest.fixture(autouse=True)
def task_client(mocker):
    return mocker.patch("phenoback.functions.iot.dragino.task_client").return_value


def test_process(ps_client):
    dragino.process_dragino(dd.SAMPLE_DATA)
    dd.SAMPLE_DATA[dd.UPLINK_KEY][dd.DECODED_PAYLOAD_KEY] = dd.DECODED_PAYLOAD

    ps_client.send.assert_called_with(dd.SAMPLE_DATA, ANY)


def test_process__no_uplink(ps_client):
    dragino.process_dragino({})

    ps_client.send.assert_not_called()


def test_decode_impl():
    decoder = dragino.DraginoDecoder(dd.SAMPLE_DATA)
    decoder.decode()
    assert decoder.decoded_payload == dd.DECODED_PAYLOAD


def test_set_uplink_frequency(task_client):
    at = datetime(2020, 1, 1)
    dragino.set_uplink_frequency(dd.DEVEUI, 60, at)

    task_client.send.assert_called_once_with(
        "",
        params={
            "DevEUI": dd.DEVEUI,
            "Payload": "0100003c",
            "FPort": 1,
        },
        at=at,
    )
