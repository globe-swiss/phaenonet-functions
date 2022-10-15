import pytest

from phenoback.functions.iot.decoder import Decoder

UPLINK = "DevEUI_uplink"
PAYLOAD = "FFAA00"
DEVEUI = "DevEUI"
TIME = "Time"
DECODED_PAYLOAD = "decoded_payload"

SAMPLE_DATA = {UPLINK: {"payload_hex": PAYLOAD, DEVEUI: DEVEUI, TIME: TIME}}


class DecoderImpl(Decoder):
    def decode_impl(self):
        return DECODED_PAYLOAD


@pytest.fixture
def decoder() -> Decoder:
    return DecoderImpl(SAMPLE_DATA)


def test_init(decoder: Decoder):
    uplink = SAMPLE_DATA[UPLINK]
    assert decoder.data == SAMPLE_DATA
    assert decoder.uplink == uplink
    assert decoder.is_uplink
    assert decoder.payload == PAYLOAD
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
        ({UPLINK: {"foo": "bar"}}, True),
        ({"downlink": {"foo": "bar"}}, False),
    ],
)
def test_is_uplink(data, expected):
    decoder = DecoderImpl(data)
    assert decoder.is_uplink == expected


@pytest.mark.parametrize(
    "payload_hex, start, length, expected",
    [
        ("00", 0, 8, 0),
        ("FF", 0, 8, 255),
        ("F0", 0, 8, 240),
        ("0F", 0, 8, 15),
        ("F0", 0, 4, 15),
        ("F0", 4, 4, 0),
        ("0F", 0, 4, 0),
        ("0F", 4, 4, 15),
    ],
)
def test_get_value(payload_hex, start, length, expected):
    decoder = DecoderImpl({UPLINK: {"payload_hex": payload_hex}})
    assert decoder.get_value(start, length) == expected
