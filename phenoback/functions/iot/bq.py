import phenoback.utils.bq


def main(data, context):  # pylint: disable=unused-argument
    phenoback.utils.bq.insert_data("iot.raw", data)
