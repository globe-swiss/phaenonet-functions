from test.functions.iot.sample_data import DraginoData as dd
from unittest.mock import ANY

import pytest

from phenoback.functions.iot import dragino


@pytest.fixture(autouse=True)
def client(mocker):
    return mocker.patch("phenoback.functions.iot.dragino.client").return_value


def test_process(client):
    dragino.process_dragino(dd.SAMPLE_DATA)
    dd.SAMPLE_DATA[dd.UPLINK_KEY][dd.DECODED_PAYLOAD_KEY] = dd.DECODED_PAYLOAD

    client.send.assert_called_with(dd.SAMPLE_DATA, ANY)


def test_process__no_uplink(client):
    dragino.process_dragino({})

    client.send.assert_not_called()


def test_decode_impl():
    decoder = dragino.DraginoDecoder(dd.SAMPLE_DATA)
    decoder.decode()
    assert decoder.decoded_payload == dd.DECODED_PAYLOAD
