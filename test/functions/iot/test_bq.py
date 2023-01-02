from phenoback.functions.iot import bq


def test_process_dragino_bq(mocker):
    encoded_data = b"eyJmb28iOiJiYXIifQ=="
    process_mock = mocker.patch("phenoback.utils.bq.insert_data")

    bq.main({"data": encoded_data}, None)

    process_mock.assert_called_with("iot.raw", {"foo": "bar"})
