import json
from typing import Set

import requests

import phenoback
from phenoback.utils import firestore as f

PROJECT_URL = "https://raw.githubusercontent.com/globe-swiss/phaenonet-client"
BRANCH = "master"

phenoback.load_credentials()


def check_translation(lang: str):
    keys = get_keys(f.get_document("definitions", "config_static"))
    translations = json.loads(
        requests.get(f"{PROJECT_URL}/{BRANCH}/src/assets/i18n/{lang}-CH.json").content
    )

    missing = [key for key in keys if not translations.get(key)]

    if missing:
        missing.sort()
        print(f"{lang} keys missing:")
        print(missing)
    else:
        print(f"{lang} translations OK.")


def get_keys(d: dict) -> Set[str]:  # pylint: disable=invalid-name
    result = set()
    for (key, value) in d.items():

        if isinstance(value, dict):
            result = result.union(get_keys(value))
        else:
            if key in ["de", "description_de"]:
                result.add(value)
    return result


check_translation("fr")
check_translation("it")
