import logging
from datetime import datetime
from typing import Set

from phenoback.utils import data as d
from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def main(data, context):
    """
    Creates an activity when an observation is created, modified or deleted in
    Firestore **and** the user or individual of that observation is being followed.
    """
    observation_id = g.get_document_id(context)
    if g.is_create_event(data):
        log.info("Add create activity for observation %s", observation_id)
        _main(data, context, "create")
    elif g.is_delete_event(data):
        log.info("Add delete activity for observation %s", observation_id)
        _main(data, context, "delete")
    elif g.is_field_updated(data, "date"):
        log.info("Add modify activity for observation %s", observation_id)
        _main(data, context, "modify")
    else:
        log.debug("No activity to add")


def _main(data, context, action):
    is_delete = action == "delete"
    process_observation(
        event_id=context.event_id,
        observation_id=g.get_document_id(context),
        individual_id=g.get_field(data, "individual_id", old_value=is_delete),
        user_id=g.get_field(data, "user", old_value=is_delete),
        phenophase=g.get_field(data, "phenophase", old_value=is_delete),
        source=g.get_field(data, "source", old_value=is_delete),
        species=g.get_field(data, "species", old_value=is_delete),
        individual=g.get_field(data, "individual", old_value=is_delete),
        action=action,
    )


def process_observation(
    event_id: str,
    observation_id: str,
    individual_id: str,
    user_id: str,
    phenophase: str,
    source: str,
    species: str,
    individual: str,
    action: str,
) -> bool:
    individual_dict = d.get_individual(individual_id)
    if not individual_dict:
        log.error(
            "Individual %s not found. Was it deleted in the meantime?", individual_id
        )
        return False
    followers = get_followers(individual, user_id)
    if followers:
        log.info("write activity %s for observation %s", event_id, observation_id)
        data = {
            "type": "observation",
            "observation_id": observation_id,
            "individual_id": individual_id,
            "user": user_id,
            "phenophase": phenophase,
            "source": source,
            "species": species,
            "activity_date": datetime.now(),
            "individual_name": individual_dict["name"],
            "phenophase_name": d.get_phenophase(species, phenophase)["de"],
            "species_name": d.get_species(species)["de"],
            "user_name": d.get_user(user_id)["nickname"],
            "action": action,
            "followers": list(followers),
        }
        f.write_document("activities", event_id, data)
        return True
    else:
        log.debug(
            "no activity written for observation %s, no followers", observation_id
        )
        return False


def get_followers(individual: str, user_id: str) -> Set[str]:
    following_users_query = f.query_collection(
        "users", "following_users", "array_contains", user_id
    )
    following_individuals_query = f.query_collection(
        "users", "following_individuals", "array_contains", individual
    )

    followers_user = {user.id for user in following_users_query.stream()}
    followers_individual = {user.id for user in following_individuals_query.stream()}

    return followers_user.union(followers_individual)
