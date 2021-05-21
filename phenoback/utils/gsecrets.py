import logging
from functools import lru_cache

from google.cloud import secretmanager

from phenoback.utils import gcloud

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
project_id = gcloud.get_project()


@lru_cache()
def get_mailer_pw():  # pragma: no cover
    log.debug("Access mailer secret")
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        name=f"projects/{project_id}/secrets/mailer_pw/versions/latest"
    )
    payload = response.payload.data.decode("UTF-8")
    return payload


@lru_cache()
def get_mailer_user():  # pragma: no cover
    log.debug("Access mailer user")
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        name=f"projects/{project_id}/secrets/mailer_user/versions/latest"
    )
    payload = response.payload.data.decode("UTF-8")
    return payload


def reset():
    log.debug("Reset all secret caches")
    get_mailer_pw.cache_clear()
    get_mailer_user.cache_clear()
