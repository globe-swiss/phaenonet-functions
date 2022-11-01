class Decoder:
    def __init__(self, data: dict):
        self._data = data
        if self.payload:
            self.int_pl = int(self.payload, 16)
            self.size = len(self.payload) * 4

    def get_value(self, start, length):
        shift = self.size - start - length
        mask = ((1 << length) - 1) << shift
        return (self.int_pl & mask) >> shift

    @property
    def data(self):
        return self._data

    @property
    def uplink(self) -> dict:
        return self.data.get("DevEUI_uplink")

    @property
    def is_uplink(self) -> bool:
        return self.uplink is not None

    @property
    def payload(self) -> str:
        return self.data.get("DevEUI_uplink", {}).get("payload_hex")

    @property
    def decoded_payload(self) -> str:
        return self.data.get("DevEUI_uplink", {}).get("decoded_payload")

    def _set_decoded_payload(self, data: dict) -> None:
        self.data["DevEUI_uplink"]["decoded_payload"] = data

    @property
    def devuei(self) -> str:
        return self.data.get("DevEUI_uplink", {}).get("DevEUI")

    @property
    def time(self) -> str:
        return self.data.get("DevEUI_uplink", {}).get("Time")

    def decode(self):
        if self.is_uplink:
            self._set_decoded_payload(self.decode_impl())
        else:
            raise ValueError("No uplink data")

    def decode_impl(self) -> dict:
        raise NotImplementedError()  # pragma: no cover
