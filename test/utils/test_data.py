# pylint: disable=protected-access
import json
from datetime import datetime

import pytest

from phenoback.utils import data as d
from phenoback.utils import firestore as f

CONFIG_STATIC_RESOURCE = "test/resources/config_static.json"
CONFIG_DYNAMIC_RESOURCE = "test/resources/config_dynamic.json"

"""
To update resource files needed for tests from phaenonet test instance
see maintenance repo @ maintenance/config/generate_config_static.py.
"""


@pytest.fixture(autouse=True)
def config_static():
    d._get_static_config.cache_clear()
    with open(CONFIG_STATIC_RESOURCE, encoding="utf-8") as file:
        data = json.loads(file.read())
        f.write_document("definitions", "config_static", data)
        return data


@pytest.fixture(autouse=True)
def config_dynamic():
    with open(CONFIG_DYNAMIC_RESOURCE, encoding="utf-8") as file:
        data = json.loads(file.read())
        f.write_document("definitions", "config_dynamic", data)
        return data


def test_update_phenoyear(config_dynamic):
    current_year = config_dynamic["phenoyear"]
    assert d.get_phenoyear(True) == current_year
    d.update_phenoyear(current_year + 1)
    assert d.get_phenoyear(False) == current_year + 1


def test_update_phenoyear__preserve_data(config_dynamic):
    assert config_dynamic["first_year"] is not None
    d.update_phenoyear(2013)
    assert (
        f.get_document("definitions", "config_dynamic")["first_year"]
        == config_dynamic["first_year"]
    )


@pytest.mark.parametrize(
    "individual, expected",
    [
        ({"some": "attribute", "last_observation_date": datetime.now()}, True),
        ({"some": "attribute"}, False),
    ],
)
def test_has_observation_date(individual, expected):
    assert d.has_observations(individual) == expected


def test_get_phenophase__cache(mocker):
    spy = mocker.spy(d, "get_document")
    assert d.get_phenophase("HS", "BEA")
    assert d.get_phenophase("HS", "BES")
    assert d.get_phenophase("BA", "BEA")
    spy.assert_called_once()  # assert results are cached


def test_get_species__cache(mocker):
    spy = mocker.spy(d, "get_document")
    assert d.get_species("HS")
    assert d.get_species("BA")
    spy.assert_called_once()  # assert results are cached


def test_follow_user__not_found():
    try:
        d.follow_user("follower_id", "followee_id")
    except ValueError:
        pass  # expected


def test_follow_user__no_array():
    follower = "follower_id"
    followee = "followee_id"
    f.write_document("users", follower, {"some_data": "data"})
    assert d.follow_user(follower, followee)
    assert followee in d.get_user(follower).get("following_users")


def test_follow_user__already_following():
    follower = "follower_id"
    followee = "followee_id"
    f.write_document("users", follower, {"following_users": [followee, "some_id"]})
    assert not d.follow_user(follower, followee)
    assert followee in d.get_user(follower).get("following_users")
    assert len(d.get_user(follower).get("following_users")) == 2


def test_follow_user():
    follower = "follower_id"
    followee = "followee_id"
    f.write_document("users", follower, {"following_users": ["some_id"]})
    assert d.follow_user(follower, followee)
    assert followee in d.get_user(follower).get("following_users")
    assert len(d.get_user(follower).get("following_users")) == 2


def test_create_user():
    user_id = "uid"
    nickname = "nick"
    firstname = "first"
    lastname = "last"
    locale = "fr-CH"
    d.create_user(user_id, nickname, firstname, lastname, locale)
    assert d.get_user(user_id) == {
        "nickname": nickname,
        "firstname": firstname,
        "lastname": lastname,
        "locale": locale,
    }


@pytest.mark.parametrize(
    "input_data, expected_output",
    [
        ({}, []),
        ({"a": {"x": "y"}}, [{"id": "a", "x": "y"}]),
        (
            {"a": {"x": "y"}, "b": {"x": "z"}},
            [{"id": "a", "x": "y"}, {"id": "b", "x": "z"}],
        ),
    ],
)
def test_to_id_array(input_data, expected_output):
    assert d.to_id_array(input_data) == expected_output


@pytest.mark.parametrize(
    "comment, expected",
    [
        ("None", True),
        ("Any Comment", True),
        ("102", False),
    ],
)
def test_is_actual_observation(comment, expected):
    assert d.is_actual_observation(comment) == expected
