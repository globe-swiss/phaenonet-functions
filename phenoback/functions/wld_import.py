import csv
import io
import logging
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Set
from zipfile import ZipFile

from google.cloud.storage import Blob

from phenoback.utils import data as d
from phenoback.utils import firestore as f
from phenoback.utils import storage as s

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


SOURCE = "wld"
NICKNAME = "PhaenoWaldWSL"
FILES = {"tree.csv", "observation_phaeno.csv", "user_id.csv", "site.csv"}
MAX_ARCHIVE_BYTES = 100000

DATA = None

SPECIES_MAP = {
    "58": "BA",
    "10": "FI",
    "60": "GE",
    "106": "HS",
    "20": "LA",
    "50": "BU",
    "82": "VB",
    "11": "WT",
    "51": "SE",
    "52": "TE",
}

PHASES_MAP = {
    "1": "BES",
    "2": "BEA",
    "3": "BLB",
    "4": "BLA",
    "5": "FRB",
    "6": "FRA",
    "7": "BVS",
    "8": "BVA",
    "9": "BFA",
}


def check_zip_archive(input_zip: ZipFile) -> None:
    filenames = input_zip.namelist()
    log.debug("Files found: %s", str(filenames))
    if not set(filenames).issubset(FILES):
        raise FileNotFoundError(f"Files found {set(filenames)} files expected {FILES}")


def check_file_size(blob: Blob) -> None:
    size = blob.size
    log.debug("Import file size %ib", size)
    if size > MAX_ARCHIVE_BYTES:
        raise OverflowError(f"File bigger than {MAX_ARCHIVE_BYTES/1000}kb")


def load_data(input_zip: ZipFile) -> Dict[str, List[dict]]:
    return {
        name: list(
            csv.DictReader(
                input_zip.read(name).decode("utf-8").splitlines(), delimiter=","
            )
        )
        for name in FILES
    }


def check_data_integrity():
    error = False
    users = {u["user_id"]: True for u in DATA["user_id.csv"]}
    sites = {s["site_id"]: True for s in DATA["site.csv"]}
    site_year_user = {}

    for row in DATA["observation_phaeno.csv"]:
        user_id = row.get("user_id")
        site_id = row.get("site_id")
        observation_id = row.get("observation_id")
        year = row.get("year")
        if not users.get(user_id):
            log.error("user_id not found: %s", user_id)
            error = True
        if not sites.get(site_id):
            log.error("site_id not found: %s", site_id)
            error = True
        if not PHASES_MAP.get(observation_id):
            log.error("observation_id not mapped to phenophase: %s", observation_id)
            error = True
        cur_value = site_year_user.get(site_id, {}).get(year)
        if cur_value and cur_value != user_id:
            log.error(
                "Multiple users for %s in %s (%s, %s)",
                site_id,
                year,
                user_id,
                cur_value,
            )
            error = True
        site_year_user.setdefault(site_id, {})[year] = user_id
    if error:
        raise ValueError("Data integrity check failed")


def import_data(pathfile: str, bucket=None):
    global DATA  # pylint: disable=global-statement
    # assumption is that the data is always provided in the following year
    year = d.get_phenoyear() - 1

    log.info("importing year %i", year)
    blob = s.get_blob(bucket, pathfile)
    check_file_size(blob)

    with ZipFile(io.BytesIO(blob.download_as_bytes()), mode="r") as input_zip:
        check_zip_archive(input_zip)
        DATA = load_data(input_zip)
    check_data_integrity()

    insert_data("public_users", public_users())
    insert_data("users", users())
    insert_data("individuals", individuals(year))
    insert_data("observations", observations(year))


@lru_cache()
def station_species() -> Dict[str, Set[str]]:
    result = {}
    for tree in DATA["tree.csv"]:
        result.setdefault(tree["site_id"], set()).add(map_species(tree["species_id"]))
    return result


@lru_cache()
def tree_species() -> Dict[str, Dict[str, str]]:
    result = {}
    for tree in DATA["tree.csv"]:
        result.setdefault(tree["site_id"], {})[tree["tree_id"]] = map_species(
            tree["species_id"]
        )
    return result


@lru_cache()
def site_users() -> Dict[str, Dict[str, str]]:
    result = {}
    for obs in DATA["observation_phaeno.csv"]:
        result.setdefault(obs["site_id"], {})[obs["year"]] = obs["user_id"]
    return result


def get_site_species(site_id: str) -> List[str]:
    return list(filter(lambda species: species, station_species()[site_id]))


def get_tree_species(site_id: str, tree_id: str) -> str:
    return tree_species()[site_id][tree_id]


def get_user(site_id: str, year: str) -> str:
    return site_users().get(site_id, {}).get(str(year))


def wsl_user(user_id) -> str:
    return f"{SOURCE}_{user_id}"


def map_species(wsl_species) -> str:
    return SPECIES_MAP.get(wsl_species, None)


def map_phenophase(wsl_observation_id):
    return PHASES_MAP[wsl_observation_id]


def individuals(year: int):
    return [
        {
            "id": f"{year}_{SOURCE}_{site['site_id']}",
            "altitude": int(site["alt"]),
            "geopos": {"lat": float(site["lat"]), "lng": float(site["long"])},
            "individual": f"{SOURCE}_{site['site_id']}",
            "name": site["site_name"],
            "source": SOURCE,
            "type": "station",
            "user": wsl_user(get_user(site["site_id"], year)),
            "year": year,
            "station_species": get_site_species(site["site_id"]),
        }
        for site in DATA["site.csv"]
        if get_user(site["site_id"], year) and get_site_species(site["site_id"])
    ]


def observations(year: int):
    return [
        {
            "id": f"{SOURCE}_{o['site_id']}_{o['tree_id']}_{o['year']}_{get_tree_species(o['site_id'], o['tree_id'])}_{map_phenophase(o['observation_id'])}",
            "individual": f"{SOURCE}_{o['site_id']}",
            "individual_id": f"{o['year']}_{SOURCE}_{o['site_id']}",
            "species": get_tree_species(o["site_id"], o["tree_id"]),
            "user": f"{SOURCE}_{o['user_id']}",
            "year": year,
            "tree_id": o["tree_id"],
            "date": datetime.strptime(o["date"], "%Y-%m-%d"),
            "phenophase": map_phenophase(o["observation_id"]),
            "source": SOURCE,
        }
        for o in DATA["observation_phaeno.csv"]
        if int(o["year"]) == year and get_tree_species(o["site_id"], o["tree_id"])
    ]


def users():
    return [
        {
            "id": wsl_user(u["user_id"]),
            "firstname": u["name_first"],
            "lastname": u["name_last"],
            "nickname": NICKNAME,
        }
        for u in DATA["user_id.csv"]
    ]


def public_users():
    return [
        {"id": wsl_user(u["user_id"]), "nickname": NICKNAME, "roles": [SOURCE]}
        for u in DATA["user_id.csv"]
    ]


def insert_data(collection: str, documents: List[dict]) -> None:
    if len(documents) == 0:
        log.error(
            "no data present on collection %s",
            collection,
        )
    else:
        log.debug("Import %i record to collection %s", len(documents), collection)
        f.write_batch(collection, "id", documents)
