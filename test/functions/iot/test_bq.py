from phenoback.functions.iot import bq


def test_process_dragino_bq(mocker, pubsub_event_data, context):
    process_mock = mocker.patch("phenoback.utils.bq.insert_data")

    bq.main(pubsub_event_data, context)

    process_mock.assert_called_with("iot.raw", {"foo": "bar"})
