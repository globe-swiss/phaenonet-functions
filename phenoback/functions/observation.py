import logging
from datetime import datetime, timezone

from phenoback.utils.data import get_individual
from phenoback.utils.firestore import update_document

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def update_last_observation(
    individual_id: str, phase: str, observation_date: datetime
) -> bool:
    individual = get_individual(individual_id)
    old_observation_date = individual.get(
        "last_observation_date", datetime.min.replace(tzinfo=timezone.utc)
    )
    if observation_date > old_observation_date:
        data = {"last_observation_date": observation_date}
        if individual.get("type") == "individual":
            data["last_phenophase"] = phase

        update_document("individuals", individual_id, data)
        log.info(
            "updated last observation for %s (%s -> %s)",
            individual_id,
            old_observation_date,
            observation_date,
        )
        return True
    else:
        log.info(
            "no update for last observation for %s (%s > %s)",
            individual_id,
            old_observation_date,
            observation_date,
        )
        return False
