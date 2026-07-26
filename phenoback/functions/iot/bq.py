from google.cloud.functions.context import Context

import phenoback.utils.bq


def main(data: dict, context: Context) -> None:  # noqa: ARG001
    phenoback.utils.bq.insert_data("iot.raw", data)
