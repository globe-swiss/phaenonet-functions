import os
import re
import subprocess  # nosec
import sys

import google.auth.credentials
import mock
from google.cloud import firestore
from xprocess import ProcessStarter

import phenoback.utils.firestore


def _get_gcloud_cmd():
    if sys.platform.startswith("win"):
        cloud_cmd = "gcloud.cmd"
    else:
        cloud_cmd = "gcloud"
    return cloud_cmd


def check():
    return "test" in os.environ["FIRESTORE_PROJECT_ID"]


def start(xprocess, name):
    class EmulatorClass(ProcessStarter):
        args = [
            _get_gcloud_cmd(),
            "beta",
            "emulators",
            "firestore",
            "start",
            "--project",
            "test",
            "--host-port",
            "localhost:8001",
        ]
        pattern = re.compile(".*is now running.*")

    logfile = xprocess.ensure(name, EmulatorClass)
    # assert environment
    print("Check emulator at startup: ", check())
    assert check(), "Connecting to the live environment?"

    credentials = mock.Mock(spec=google.auth.credentials.Credentials)
    phenoback.utils.firestore._db = (  # pylint: disable=protected-access
        firestore.Client(project="test", credentials=credentials)
    )

    yield logfile
    # shutdown emulator
    # post('http://localhost:8001/shutdown')
    # shutdown via post request doesn't work anymore with firestore emulator, process needs to be killed
    try:
        subprocess.call(["pkill", "-f", "java"])  # nosec
    except FileNotFoundError:
        print(
            "WARNING: procps not installed. you may need to manually kill the firestore emulator"
        )


def _setup_environment():
    os.environ["FIRESTORE_DATASET"] = "test"
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8001"
    os.environ["FIRESTORE_EMULATOR_HOST_PATH"] = "localhost:8001/firestore"
    os.environ["FIRESTORE_HOST"] = "http://localhost:8001"
    os.environ["FIRESTORE_PROJECT_ID"] = "test"


_setup_environment()
