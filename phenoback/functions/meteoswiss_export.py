"""
Meteoswiss phenology data export

New PhaenoNet data mapped as good as possible to the previously existing export structure for meteoswiss.
"""

import csv
import io
import logging

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.utils import storage
from phenoback.utils.data import query_individuals, query_observation

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def main(event, context):  # pylint: disable=unused-argument
    process()


def process(year: int = None):
    if not year:
        year = d.get_phenoyear()

    observations = []
    for observation_doc in (
        query_observation("year", "==", year)
        .where(filter=f.FieldFilter("source", "==", "globe"))
        .stream()
    ):
        observation_dict = observation_doc.to_dict()
        observations.append(observation_dict)

    individuals_map = {}
    for individual_doc in (
        query_individuals("year", "==", year)
        .where(filter=f.FieldFilter("source", "==", "globe"))
        .stream()
    ):
        individual_dict = individual_doc.to_dict()
        individuals_map[individual_dict["individual"]] = individual_dict

    results = []
    for o in observations:  # pylint: disable=invalid-name
        try:
            i = individuals_map[o["individual"]]
            results.append(
                {
                    "OWNER": o["user"],
                    "MEAS_OBJ_ID": o["individual"],
                    "PLACENAME": i["name"],
                    "MEAS_YEAR": o["year"],
                    "MEAS_SPEC_ID": o["species"],
                    "MEAS_PPH_1": o["phenophase"],
                    "MEAS_ID": "",
                    "MEAS_DATE": d.localtime(o["date"]).strftime("%d.%m.%Y"),
                    "MEAS_ALTGRP": "",
                    "MEAS_INCR": "",
                    "CREATED": d.localtime(o["created"]).strftime("%d.%m.%Y %H:%M:%S"),
                    "MODIFIED": (
                        d.localtime(o["modified"]).strftime("%d.%m.%Y %H:%M:%S")
                        if o["modified"]
                        else ""
                    ),
                    "GEOPOS": f"{i['geopos']['lat']},{i['geopos']['lng']}",
                    "ALTITUDE": i["altitude"],
                    "DESCRIPTION": i["description"],
                    "EXPOSITION": i["exposition"],
                    "GRADIENT": i["gradient"],
                    "SHADE": i["shade"],
                    "WATERING": i["watering"],
                    "LESS100": i["less100"],
                    "HABITAT": i["habitat"],
                    "FOREST": i["forest"],
                    "SPEC_ID": i["species"],
                    "ID": "",
                    "PARENT_ID": "",
                    "MEAS_PPH_2": "",
                    "NAME_DE": d.get_phenophase(o["species"], o["phenophase"])["de"],
                    "NAME_FR": "",
                    "NAME_EN": "",
                    "NAME_IT": "",
                    "FUNCTION": "MS_DATE",
                    "IN_SEQUENCE": "",
                    "MODIFIED_1": "",
                    "TENANT": "GLOBE_CH",
                    "FIRSTNAME": "",
                    "LASTNAME": "",
                    "ORGANISATION": "",
                    "MODIFIED_2": "",
                    "SPEC_SET_TENANT": d.get_species(o["species"])["de"],
                    "SPEC_SET_DE": "",
                    "SPEC_SET_FR": "",
                    "SPEC_SET_EN": "",
                    "SPEC_SET_IT": "",
                }
            )
        except Exception:  # pylint: disable=broad-except
            log.error("Error processing observation, skipping %s", o, exc_info=True)

    if results:
        with io.StringIO() as csv_string:
            dict_writer = csv.DictWriter(csv_string, results[0].keys(), delimiter=";")
            dict_writer.writeheader()
            dict_writer.writerows(results)

            storage.upload_string(
                None,
                f"public/meteoswiss/export_{year}.csv",
                csv_string.getvalue(),
                content_type="text/csv",
            )
    else:
        log.error("No data to export for %i", year)
