import logging
from test import emulator

import pytest
from requests import delete


@pytest.fixture(scope="session", autouse=True)
def emulator_process(xprocess):
    yield from emulator.start(xprocess, "firestore")


@pytest.fixture(autouse=True)
def clear_emulator_data():
    delete(
        "http://localhost:8001/emulator/v1/projects/test/databases/(default)/documents",
        timeout=10,
    )


@pytest.fixture()
def caperrors(caplog):
    caplog.set_level(logging.ERROR)
    return caplog


@pytest.fixture()
def capwarnings(caplog):
    caplog.set_level(logging.WARNING)
    return caplog


@pytest.fixture(autouse=True)
def gcp_project(mocker) -> None:
    project = "project"
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=project)
    return project


@pytest.fixture(autouse=True)
def gcp_location(mocker) -> None:
    location = "location"
    mocker.patch("phenoback.utils.gcloud.get_location", return_value=location)
    return location


@pytest.fixture(autouse=True)
def mock_requests(mocker):
    mocker.patch("requests.post")
    mocker.patch("requests.get")
