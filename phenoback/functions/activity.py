import logging
from datetime import datetime
from typing import Set

from phenoback.utils.data import get_individual, get_phenophase, get_species, get_user
from phenoback.utils.firestore import query_collection, write_document

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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
    individual_dict = get_individual(individual_id)
    if not individual_dict:
        log.error(
            "Individual %s not found. Was it deleted in the meantime?", individual_id
        )
        return
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
            "phenophase_name": get_phenophase(species, phenophase)["de"],
            "species_name": get_species(species)["de"],
            "user_name": get_user(user_id)["nickname"],
            "action": action,
            "followers": list(followers),
        }
        write_document("activities", event_id, data)
        return True
    else:
        log.debug(
            "no activity written for observation %s, no followers", observation_id
        )
        return False


def get_followers(individual: str, user_id: str) -> Set[str]:
    following_users_query = query_collection(
        "users", "following_users", "array_contains", user_id
    )
    following_individuals_query = query_collection(
        "users", "following_individuals", "array_contains", individual
    )

    followers_user = {user.id for user in following_users_query.stream()}
    followers_individual = {user.id for user in following_individuals_query.stream()}

    return followers_user.union(followers_individual)
