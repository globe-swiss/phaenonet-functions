import logging
from functools import lru_cache

from google.cloud import secretmanager

from phenoback.utils import gcloud

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@lru_cache
def get_secret(key: str):
    log.debug("Access %s", key)
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        name=f"projects/{gcloud.get_project()}/secrets/{key}/versions/latest"
    )
    payload = response.payload.data.decode("UTF-8")
    return payload


def get_mailer_pw():  # pragma: no cover
    return get_secret("mailer_pw")


def get_mailer_user():  # pragma: no cover
    return get_secret("mailer_user")


def get_tinify_apikey():  # pragma: no cover
    return get_secret("tinify_apikey")


def reset():
    log.debug("Reset all secret caches")
    get_secret.cache_clear()
