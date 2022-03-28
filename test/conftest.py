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
        "http://localhost:8001/emulator/v1/projects/test/databases/(default)/documents"
    )


@pytest.fixture()
def caperrors(caplog):
    caplog.set_level(logging.ERROR)
    return caplog


@pytest.fixture()
def capwarnings(caplog):
    caplog.set_level(logging.WARNING)
    return caplog
