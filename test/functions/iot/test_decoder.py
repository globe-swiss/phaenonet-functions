import pytest

from phenoback.functions.iot.decoder import Decoder

UPLINK_KEY = "DevEUI_uplink"
PAYLOAD_HEX_KEY = "payload_hex"
PAYLOAD_HEX = "FFAA00"
DEVEUI = "DevEUI"
TIME = "Time"
DECODED_PAYLOAD = "decoded_payload"

SAMPLE_DATA = {UPLINK_KEY: {PAYLOAD_HEX_KEY: PAYLOAD_HEX, DEVEUI: DEVEUI, TIME: TIME}}


class DecoderImpl(Decoder):
    def decode_impl(self):
        return DECODED_PAYLOAD


@pytest.fixture
def decoder() -> Decoder:
    return DecoderImpl(SAMPLE_DATA)


def test_init(decoder: Decoder):
    assert decoder.is_uplink
    assert decoder.data == SAMPLE_DATA
    assert decoder.uplink == SAMPLE_DATA[UPLINK_KEY]
    assert decoder.payload == PAYLOAD_HEX
    assert decoder.devuei == DEVEUI
    assert decoder.time == TIME

    assert decoder.int_pl == 16755200
    assert decoder.size == 24


def test_decode(decoder: Decoder):
    decoder.decode()
    assert decoder.decoded_payload == DECODED_PAYLOAD


def test_decode__no_uplink():
    decoder = DecoderImpl({})
    with pytest.raises(ValueError):
        decoder.decode()


@pytest.mark.parametrize(
    "data, expected",
    [
        ({UPLINK_KEY: {"foo": "bar"}}, True),
        ({"downlink": {"foo": "bar"}}, False),
    ],
)
def test_is_uplink(data, expected):
    decoder = DecoderImpl(data)
    assert decoder.is_uplink == expected


@pytest.mark.parametrize(
    "payload_hex, start, length, signed, expected",
    [
        ("00", 0, 8, False, 0),
        ("FF", 0, 8, False, 255),
        ("F0", 0, 8, False, 240),
        ("0F", 0, 8, False, 15),
        ("F0", 0, 4, False, 15),
        ("F0", 4, 4, False, 0),
        ("0F", 0, 4, False, 0),
        ("0F", 4, 4, False, 15),
        ("00", 0, 8, True, 0),
        ("FF", 0, 8, True, -1),
        ("F0", 0, 8, True, -16),
        ("0F", 0, 8, True, 15),
        ("F0", 0, 4, True, -1),
        ("F0", 4, 4, True, 0),
        ("0F", 0, 4, True, 0),
        ("0F", 4, 4, True, -1),
    ],
)
def test_get_value(payload_hex, start, length, signed, expected):
    decoder = DecoderImpl({UPLINK_KEY: {PAYLOAD_HEX_KEY: payload_hex}})
    assert decoder.get_value(start, length, signed=signed) == expected
