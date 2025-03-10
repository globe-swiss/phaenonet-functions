import logging
from collections import defaultdict

import requests

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

REQUEST_TIMEOUT = 5


def main(data, context):  # pylint: disable=unused-argument
    send_permarobotics(data)


def send_permarobotics(data: dict) -> bool:
    deveui = data["DevEUI_uplink"]["DevEUI"]
    result = defaultdict(dict)
    result["end_device_ids"]["dev_eui"] = deveui
    result["uplink_message"]["received_at"] = data["DevEUI_uplink"]["Time"]
    result["uplink_message"]["rx_metadata"] = [
        {
            "rssi": data["DevEUI_uplink"]["LrrRSSI"],
            "snr": data["DevEUI_uplink"]["LrrSNR"],
            "esp": data["DevEUI_uplink"]["LrrESP"],
            "spfact": data["DevEUI_uplink"]["SpFact"],
        }
    ]
    result["uplink_message"]["f_port"] = data["DevEUI_uplink"]["FPort"]
    result["uplink_message"]["f_cnt"] = data["DevEUI_uplink"]["FCntUp"]
    result["uplink_message"]["frm_payload"] = data["DevEUI_uplink"]["payload_hex"]
    result["uplink_message"]["decoded_payload"] = data["DevEUI_uplink"][
        "decoded_payload"
    ]
    resp = requests.post(
        url="https://europe-west3-permarobotics.cloudfunctions.net/saveSensorData",
        json=result,
        timeout=REQUEST_TIMEOUT,
    )
    if resp.ok:
        log.debug("Send data permarobotics ok: %s", deveui)
        return True
    else:
        log.error(
            "send data permarobotics error: code=%i, text=%s",
            resp.status_code,
            resp.text,
        )
        return False
