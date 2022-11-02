__all__ = ["functions", "utils"]
import logging
import os

import firebase_admin
from firebase_admin import credentials

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

_PROJECT = "phaenonet-test"
_TYPE = "firebase-adminsdk"

default_credential_file = os.path.join(
    os.path.dirname(__file__), "..", "credentials", f"{_PROJECT}-{_TYPE}.json"
)


def load_credentials(
    credential_file: str = default_credential_file,
) -> None:  # pragma: no cover
    if os.path.isfile(credential_file):

        cred = credentials.Certificate(credential_file)
        firebase_admin.initialize_app(
            cred, {"storageBucket": f"{cred.project_id}.appspot.com"}
        )

        log.info("app initialized with local credentials %s", credential_file)


def set_credential_env(
    credential_file: str = default_credential_file,
) -> None:  # pragma: no cover
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_file
    os.environ["GCP_PROJECT"] = _PROJECT
