from phenoback.utils.firestore import get_document


def get_phenophase(species: str, phenophase: str) -> dict:
    return get_document('definitions/individuals/species/%s/phenophases' % species, phenophase)


def get_species(species: str) -> dict:
    return get_document('definitions/individuals/species', species)


def get_individual(individual_id: str) -> dict:
    return get_document('individuals', individual_id)


def get_observation(observation_id: str) -> dict:
    return get_document('observations', observation_id)


def get_user(user_id: str) -> dict:
    return get_document('users', user_id)
