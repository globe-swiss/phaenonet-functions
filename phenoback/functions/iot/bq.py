import phenoback.utils.bq
import phenoback.utils.gcloud as g


def main(event, context):  # pylint: disable=unused-argument
    json_data = g.get_data(event)
    phenoback.utils.bq.insert_data("iot.raw", json_data)
