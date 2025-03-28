# pylint: disable=import-outside-toplevel
import logging
from test import emulator

import pytest
import strictyaml as yaml
from requests import delete

import phenoback.utils.firestore as f
import phenoback.utils.gcloud as g


@pytest.fixture(scope="session", autouse=True)
def emulator_process(xprocess):
    yield from emulator.start(xprocess, "firestore")


@pytest.fixture(autouse=True)
def clear_emulator_data():
    delete(
        "http://localhost:8001/emulator/v1/projects/test/databases/(default)/documents",
        timeout=10,
    )


@pytest.fixture(autouse=True)
def mock_main(mocker):
    import firebase_admin
    import sentry_sdk

    from phenoback.utils import glogging

    firebase_admin.initialize_app = mocker.Mock()
    glogging.init = mocker.Mock()
    sentry_sdk.init = mocker.Mock()

    import main  # pylint: disable=unused-import


@pytest.fixture()
def caperrors(caplog):
    caplog.set_level(logging.ERROR)
    return caplog


@pytest.fixture()
def capwarnings(caplog):
    caplog.set_level(logging.WARNING)
    return caplog


@pytest.fixture(autouse=True)
def gcp_project(mocker) -> str:
    project = "project-name"
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=project)
    return project


@pytest.fixture(autouse=True)
def gcp_location(mocker) -> str:
    location = "location"
    mocker.patch("phenoback.utils.gcloud.get_location", return_value=location)
    return location


@pytest.fixture(autouse=False)
def phenoyear():
    year = 2000
    f.write_document("definitions", "config_dynamic", {"phenoyear": year})
    return year


@pytest.fixture(autouse=True)
def mock_requests(mocker):
    mocker.patch("requests.post")
    mocker.patch("requests.get")


@pytest.fixture()
def context():
    return g.Context(eventId="ignored", resource="document_path/document_id")


@pytest.fixture()
def data():
    return {"foo": "bar"}


@pytest.fixture()
def pubsub_event():
    return {"data": b"eyJmb28iOiJiYXIifQ=="}  # {"foo": "bar"}


@pytest.fixture()
def pubsub_event_data():
    return g.get_data({"data": b"eyJmb28iOiJiYXIifQ=="})  # {"foo": "bar"}


def readfile(filename: str):
    with open(filename, encoding="utf-8") as file:
        return file.read()


@pytest.fixture
def deploy_yaml():
    return yaml.load(readfile(".github/workflows/deploy-function.yml"))


@pytest.fixture
def main_yaml():
    return yaml.load(readfile(".github/workflows/main.yml"))


@pytest.fixture
def matrix_includes(deploy_yaml):
    return deploy_yaml["jobs"]["deploy"]["strategy"]["matrix"]["include"]


@pytest.fixture
def gcf_names(matrix_includes):
    return [matrix_include["name"].data for matrix_include in matrix_includes]
