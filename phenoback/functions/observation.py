import logging
from typing import Optional

import phenoback.utils.data as d
import phenoback.utils.firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def updated_observation(individual_id: str):
    individual = d.get_individual(individual_id)
    if individual:
        last_observation = _get_last_observation(individual_id)

        if last_observation:
            new_phenophase = last_observation.get("phenophase")
            new_observation_date = last_observation.get("date")
        else:
            new_phenophase = f.DELETE_FIELD
            new_observation_date = f.DELETE_FIELD

        old_observation_date = individual.get("last_observation_date")

        data = {"last_observation_date": new_observation_date}
        if individual.get("type") == "individual":
            data["last_phenophase"] = new_phenophase

        d.update_individual(individual_id, data)
        log.info(
            "updated last observation for %s (%s -> %s)",
            individual_id,
            old_observation_date,
            new_observation_date,
        )
    else:
        log.warning(
            "Could not find individual %s, may have been already deleted.",
            individual_id,
        )


def _get_last_observation(individual_id: str) -> Optional[dict]:
    last_obs_query = d.query_observation("individual_id", "==", individual_id)
    result = None
    for observation_doc in last_obs_query.stream():
        observation = observation_doc.to_dict()
        if not result or observation.get("date") > result.get("date"):
            result = observation
    return result
