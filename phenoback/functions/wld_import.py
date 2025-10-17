import csv
import io
import logging
from datetime import datetime
from functools import lru_cache
from zipfile import ZipFile

from google.cloud.storage import Blob

from phenoback.utils import data as d
from phenoback.utils import firestore as f
from phenoback.utils import storage as s

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


SOURCE = "wld"
NICKNAME = "PhaenoWaldWSL"
FILES = {"tree.csv", "observation_phaeno.csv", "user_id.csv", "site.csv"}
MAX_ARCHIVE_BYTES = 100000

loaded_data = None

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


def main(data, context):  # pylint: disable=unused-argument
    """
    Import wld data on file upload to private/wld_import
    """
    pathfile = data["name"]
    if pathfile.startswith("private/wld_import/"):
        log.info("Import wld data for %s", pathfile)
        import_data(pathfile)


def check_zip_archive(input_zip: ZipFile) -> None:
    """
    Validates that the ZIP archive contains all required files.

    :param input_zip: ZipFile object to validate
    :raises FileNotFoundError: If required files are missing from the archive
    """
    filenames = input_zip.namelist()
    log.debug("Files found: %s", str(filenames))
    if not set(FILES).issubset(filenames):
        raise FileNotFoundError(f"Files found {set(filenames)} files expected {FILES}")


def check_file_size(blob: Blob) -> None:
    """
    Checks if the uploaded file size is within acceptable limits.

    :param blob: Google Cloud Storage blob to check
    :raises OverflowError: If file size exceeds MAX_ARCHIVE_BYTES
    """
    size = blob.size
    log.debug("Import file size %ib", size)
    if size > MAX_ARCHIVE_BYTES:
        raise OverflowError(f"File bigger than {MAX_ARCHIVE_BYTES / 1000}kb")


def load_data(input_zip: ZipFile) -> dict[str, list[dict]]:
    """
    Loads CSV data from the ZIP archive into a dictionary.

    :param input_zip: ZipFile containing CSV files
    :returns: Dictionary mapping filenames to lists of dictionaries representing CSV rows
    """
    return {
        name: list(
            csv.DictReader(
                input_zip.read(name).decode("utf-8").splitlines(), delimiter=","
            )
        )
        for name in FILES
    }


def check_data_integrity():
    """
    Validates data integrity across all imported CSV files.

    Checks:
    - All user_ids in observations exist in users file
    - All site_ids in observations exist in sites file
    - All tree_ids in observations exist in trees file
    - All observation_ids map to valid phenophases
    - No multiple users have observations for same site in same year
    - Tree ID format is correct

    :raises ValueError: If any data integrity check fails
    """
    error = False
    users = {u["user_id"]: True for u in loaded_data["user_id.csv"]}
    sites = {s["site_id"]: True for s in loaded_data["site.csv"]}
    trees = {f"${s['site_id']},${s['tree_id']}": True for s in loaded_data["tree.csv"]}
    site_year_user = {}

    for row in loaded_data["observation_phaeno.csv"]:
        user_id = row.get("user_id")
        site_id = row.get("site_id")
        tree_id = row.get("tree_id")
        observation_id = row.get("observation_id")
        year = row.get("year")
        if not users.get(user_id):
            log.error("user_id not found: %s", user_id)
            error = True
        if not sites.get(site_id):
            log.error("site_id not found: %s", site_id)
            error = True
        if not trees.get(f"${site_id},${tree_id}"):
            log.error("tree not found: site_id=%s, tree_id=%s", site_id, tree_id)
            error = True
        if not PHASES_MAP.get(observation_id):
            log.error("observation_id not mapped to phenophase: %s", observation_id)
            error = True
        cur_value = site_year_user.get(site_id, {}).get(year)
        if cur_value and cur_value != user_id:
            log.error(
                "Multiple users have observations for site %s in %s (%s, %s)",
                site_id,
                year,
                user_id,
                cur_value,
            )
            error = True
        site_year_user.setdefault(site_id, {})[year] = user_id
        # tree_id is a composed key of ${statcode}_${tree_id}
        if len(tree_id.split("_", 1)) != 2:
            log.error("wrong tree_id format: %s", tree_id)
            error = True

    if len(loaded_data["tree.csv"]) != len(trees.keys()):
        log.error("Duplicate entries in trees file")
        error = True

    if error:
        raise ValueError("Data integrity check failed")


def import_data(pathfile: str, bucket=None, year: int | None = None):
    """
    Main import function that processes WLD data from a ZIP file.

    :param pathfile: Path to the ZIP file in cloud storage
    :param bucket: Optional GCS bucket (defaults to configured bucket)
    :param year: Year to import data for (defaults to previous phenological year)
    """
    global loaded_data  # pylint: disable=global-statement
    # default to previous year if not specified
    if year is None:
        year = d.get_phenoyear() - 1

    log.info("importing year %i", year)
    blob = s.get_blob(bucket, pathfile)
    check_file_size(blob)

    with ZipFile(io.BytesIO(blob.download_as_bytes()), mode="r") as input_zip:
        check_zip_archive(input_zip)
        loaded_data = load_data(input_zip)
    check_data_integrity()

    insert_data("public_users", public_users())
    insert_data("users", users())
    insert_data("individuals", individuals(year))
    insert_data("observations", observations(year))


@lru_cache
def station_species() -> dict[str, set[str]]:
    """
    Creates a mapping of site IDs to sets of species present at each site.

    :returns: Dictionary mapping site_id to set of species codes
    """
    result = {}
    for tree in loaded_data["tree.csv"]:
        result.setdefault(tree["site_id"], set()).add(map_species(tree["species_id"]))
    return result


@lru_cache
def tree_species() -> dict[str, dict[str, str]]:
    """
    Creates a nested mapping of site IDs to tree IDs to species.

    :returns: Dictionary mapping site_id -> tree_id -> species code
    """
    result = {}
    for tree in loaded_data["tree.csv"]:
        result.setdefault(tree["site_id"], {})[tree["tree_id"]] = map_species(
            tree["species_id"]
        )
    return result


@lru_cache
def site_users() -> dict[str, dict[str, str]]:
    """
    Creates a mapping of site IDs to years to user IDs.

    :returns: Dictionary mapping site_id -> year -> user_id
    """
    result = {}
    for obs in loaded_data["observation_phaeno.csv"]:
        result.setdefault(obs["site_id"], {})[obs["year"]] = obs["user_id"]
    return result


def get_site_species(site_id: str) -> list[str]:
    """
    Gets list of species present at a specific site.

    :param site_id: ID of the site
    :returns: List of species codes (filtered to remove None values)
    """
    return list(filter(lambda species: species, station_species()[site_id]))


def get_tree_species(site_id: str, tree_id: str) -> str:
    """
    Gets the species of a specific tree at a site.

    :param site_id: ID of the site
    :param tree_id: ID of the tree
    :returns: Species code for the tree
    """
    return tree_species()[site_id][tree_id]


def get_user(site_id: str, year: str) -> str:
    """
    Gets the user ID who made observations at a site in a specific year.

    :param site_id: ID of the site
    :param year: Year as string
    :returns: User ID or None if no user found
    """
    return site_users().get(site_id, {}).get(str(year))


def wsl_user(user_id) -> str:
    """
    Formats a WSL user ID with the source prefix.

    :param user_id: Original user ID
    :returns: Formatted user ID with 'wld_' prefix
    """
    return f"{SOURCE}_{user_id}"


def map_species(wsl_species) -> str:
    """
    Maps WSL species ID to internal species code.

    :param wsl_species: WSL species ID
    :returns: Internal species code or None if not mapped
    """
    return SPECIES_MAP.get(wsl_species, None)


def map_phenophase(wsl_observation_id):
    """
    Maps WSL observation ID to internal phenophase code.

    :param wsl_observation_id: WSL observation ID
    :returns: Internal phenophase code
    """
    return PHASES_MAP[wsl_observation_id]


def individuals(year: int):
    """
    Creates individual records for all sites with observations in the given year.

    :param year: Year to process
    :returns: List of individual dictionaries ready for Firestore insertion
    """
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
        for site in loaded_data["site.csv"]
        if get_user(site["site_id"], year) and get_site_species(site["site_id"])
    ]


def observations(year: int):
    """
    Creates observation records for the given year.

    :param year: Year to filter observations
    :returns: List of observation dictionaries ready for Firestore insertion
    """
    return [
        {
            "id": f"{SOURCE}_{o['site_id']}_{o['tree_id']}_{o['year']}_{get_tree_species(o['site_id'], o['tree_id'])}_{map_phenophase(o['observation_id'])}",
            "individual": f"{SOURCE}_{o['site_id']}",
            "individual_id": f"{o['year']}_{SOURCE}_{o['site_id']}",
            "species": get_tree_species(o["site_id"], o["tree_id"]),
            "user": f"{SOURCE}_{o['user_id']}",
            "year": year,
            "tree_id": o["tree_id"].split("_", 1)[1],
            "date": d.localtime(datetime.strptime(o["date"], "%Y-%m-%d")),
            "phenophase": map_phenophase(o["observation_id"]),
            "source": SOURCE,
        }
        for o in loaded_data["observation_phaeno.csv"]
        if int(o["year"]) == year and get_tree_species(o["site_id"], o["tree_id"])
    ]


def users():
    """
    Creates user records from imported user data.

    :returns: List of user dictionaries with formatted IDs and names
    """
    return [
        {
            "id": wsl_user(u["user_id"]),
            "firstname": u["name_first"],
            "lastname": u["name_last"],
            "nickname": NICKNAME,
        }
        for u in loaded_data["user_id.csv"]
    ]


def public_users():
    """
    Creates public user records with limited information.

    :returns: List of public user dictionaries with ID, nickname, and roles
    """
    return [
        {"id": wsl_user(u["user_id"]), "nickname": NICKNAME, "roles": [SOURCE]}
        for u in loaded_data["user_id.csv"]
    ]


def insert_data(collection: str, documents: list[dict]) -> None:
    """
    Batch inserts documents into a Firestore collection.

    :param collection: Name of the Firestore collection
    :param documents: List of documents to insert
    """
    if len(documents) == 0:
        log.error(
            "no data present on collection %s",
            collection,
        )
    else:
        log.debug("Import %i record to collection %s", len(documents), collection)
        f.write_batch(collection, "id", documents)
