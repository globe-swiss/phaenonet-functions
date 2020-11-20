# pylint: disable=unused-argument,protected-access
import json
from datetime import datetime

import pytest

from phenoback.utils import data as d
from phenoback.utils import firestore as f

CONFIG_STATIC_RESOURCE = "test/resources/config_static.json"
CONFIG_DYNAMIC_RESOURCE = "test/resources/config_dynamic.json"


@pytest.fixture
def static_config():
    d._get_static_config.cache_clear()
    with open(CONFIG_STATIC_RESOURCE, "r") as file:
        data = json.loads(file.read())
        f.write_document("definitions", "config_static", data)
        return data


@pytest.fixture
def dynamic_config():
    d._get_dynamic_config.cache_clear()
    with open(CONFIG_DYNAMIC_RESOURCE, "r") as file:
        data = json.loads(file.read())
        f.write_document("definitions", "config_dynamic", data)
        return data


def test_update_get_phenoyear():
    data = {"important": "stuff is not removed"}
    f.write_document("definitions", "config_dynamic", data)
    d.update_phenoyear(2013)
    assert d.get_phenoyear() == 2013


def test_update_phenoyear__preserve_data():
    data = {"important": "stuff is not removed"}
    f.write_document("definitions", "config_dynamic", data)
    d.update_phenoyear(2013)
    result = f.get_document("definitions", "config_dynamic")
    assert result["important"] == "stuff is not removed"


@pytest.mark.parametrize(
    "individual, expected",
    [
        ({"some": "attribute", "last_observation_date": datetime.now()}, True),
        ({"some": "attribute"}, False),
    ],
)
def test_has_observation_date(individual, expected):
    assert d.has_observations(individual) == expected


def test_get_phenophase__cache(mocker, static_config):
    spy = mocker.spy(d, "get_document")
    assert d.get_phenophase("HS", "BEA")
    assert d.get_phenophase("HS", "BES")
    assert d.get_phenophase("BA", "BEA")
    spy.assert_called_once()  # assert results are cached


def test_get_species__cache(mocker, static_config):
    spy = mocker.spy(d, "get_document")
    assert d.get_species("HS")
    assert d.get_species("BA")
    spy.assert_called_once()  # assert results are cached


def test_get_phenoyear__cache(mocker, dynamic_config):
    spy = mocker.spy(d, "get_document")
    phenoyear = d.get_phenoyear()
    assert d.get_phenoyear() == phenoyear
    spy.assert_called_once()  # assert results are cached


def update_resources():
    """
    Updates resource files needed for tests from phenonet test instance.
    Run from the base folder for the file to be written in the correct
    location e.g. `python /workspaces/phaenonet-functions/test/test_data.py`.
    """
    import phenoback  # pylint: disable=import-outside-toplevel

    phenoback.load_credentials()
    with open(CONFIG_STATIC_RESOURCE, "w") as file:
        file.write(
            json.dumps(
                f.get_document("definitions", "config_static"), indent=2, sort_keys=True
            )
        )
    with open(CONFIG_DYNAMIC_RESOURCE, "w") as file:
        file.write(
            json.dumps(
                f.get_document("definitions", "config_dynamic"),
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    update_resources()
