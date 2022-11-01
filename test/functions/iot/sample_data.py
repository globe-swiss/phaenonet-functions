class DraginoData:
    UPLINK_KEY = "DevEUI_uplink"
    DEVEUI = "DevEUI"
    TIME = "Time"
    PAYLOAD_HEX = "01b4034001f30800fc01b821"
    PAYLOAD_HEX_KEY = "payload_hex"
    DECODED_PAYLOAD_KEY = "decoded_payload"

    DECODED_PAYLOAD = {
        "soilHumidity": {"value": 7.27, "unit": "%"},
        "soilTemperature": {"value": 33.2, "unit": "°C"},
        "airHumidity": {"value": 44.0, "unit": "%"},
        "airTemperature": {"value": 25.2, "unit": "°C"},
        "batteryVoltage": {"value": 3.3, "unit": "V"},
    }

    SAMPLE_DATA = {
        UPLINK_KEY: {
            PAYLOAD_HEX_KEY: PAYLOAD_HEX,
            DEVEUI: DEVEUI,
            TIME: TIME,
        }
    }
