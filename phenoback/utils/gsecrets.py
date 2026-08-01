import logging
from functools import lru_cache

from google.cloud import secretmanager

from phenoback.utils import gcloud

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@lru_cache
def get_secret(key: str) -> str:
    log.debug("Access %s", key)
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        name=f"projects/{gcloud.get_project()}/secrets/{key}/versions/latest"
    )
    return response.payload.data.decode("UTF-8")


def get_mailer_pw() -> str:  # pragma: no cover
    return get_secret("mailer_pw")


def get_mailer_user() -> str:  # pragma: no cover
    return get_secret("mailer_user")


def get_tinify_apikey() -> str:  # pragma: no cover
    return get_secret("tinify_apikey")


def reset() -> None:
    log.debug("Reset all secret caches")
    get_secret.cache_clear()
