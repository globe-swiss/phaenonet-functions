import logging
from datetime import datetime, timezone
from typing import Optional

import phenoback.utils.data as d
import phenoback.utils.firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def _update_individual(
    individual_id: str,
    individual_type: str,
    phase: str,
    old_observation_date: datetime,
    new_observation_date: datetime,
):
    data = {"last_observation_date": new_observation_date}
    if individual_type == "individual":
        data["last_phenophase"] = phase

    d.update_individual(individual_id, data)
    log.info(
        "updated last observation for %s (%s -> %s)",
        individual_id,
        old_observation_date,
        new_observation_date,
    )


def updated_observation(
    individual_id: str, phase: str, observation_date: datetime
) -> bool:
    individual = d.get_individual(individual_id)
    old_observation_date = individual.get(
        "last_observation_date", datetime.min.replace(tzinfo=timezone.utc)
    )
    if observation_date >= old_observation_date:
        _update_individual(
            individual_id,
            individual.get("type"),
            phase,
            old_observation_date,
            observation_date,
        )
        return True
    else:
        log.info(
            "update: no update for last observation for %s (%s > %s)",
            individual_id,
            old_observation_date,
            observation_date,
        )
        return False


def removed_observation(individual_id: str, observation_date: datetime) -> bool:
    individual = d.get_individual(individual_id)
    old_observation_date = individual.get(
        "last_observation_date", datetime.min.replace(tzinfo=timezone.utc)
    )
    if observation_date == old_observation_date:
        last_observation = _get_last_observation(individual_id)
        individual_type = individual.get("type")
        if last_observation:
            new_phenophase = last_observation.get("phenophase")
            new_observation_date = last_observation.get("date")
        else:
            new_phenophase = f.DELETE_FIELD
            new_observation_date = f.DELETE_FIELD
        _update_individual(
            individual_id,
            individual_type,
            new_phenophase,
            old_observation_date,
            new_observation_date,
        )
        return True
    else:
        log.debug(
            "remove: no update for last observation for %s (%s != %s)",
            individual_id,
            old_observation_date,
            observation_date,
        )
        return False


def _get_last_observation(individual_id: str) -> Optional[dict]:
    last_obs_query = (
        d.query_observation("individual_id", "==", individual_id)
        .order_by("date", "DESCENDING")
        .limit(1)
    )
    for obs in last_obs_query.stream():
        print(obs.to_dict())
        return obs.to_dict()
    return None
