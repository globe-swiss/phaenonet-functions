# pylint: disable=protected-access
import json
import test
from datetime import datetime, date

import pytest
import pytz

from phenoback.utils import data as d
from phenoback.utils import firestore as f


@pytest.fixture(autouse=True)
def config_static():
    """
    To update resource files needed for tests from phaenonet test instance
    see maintenance repo @ maintenance/config/generate_config_static.py.
    """
    d._get_static_config.cache_clear()
    with open(test.get_resource_path("config_static.json"), encoding="utf-8") as file:
        data = json.loads(file.read())
        f.write_document("definitions", "config_static", data)
        return data


@pytest.fixture(autouse=True)
def config_dynamic():
    with open(test.get_resource_path("config_dynamic.json"), encoding="utf-8") as file:
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


def test_localtime__no_input():
    # Test localtime() without input returns current time in Europe/Zurich
    result = d.localtime()
    assert isinstance(result, datetime)
    # Assert not naive
    assert result.tzinfo


def test_localtime__with_naive_datetime():
    # Test with naive datetime (no timezone) - should convert to Europe/Zurich
    naive_dt = datetime(2024, 1, 15, 10, 30, 0)
    result = d.localtime(naive_dt)
    assert result.tzinfo
    assert result.hour == 10
    assert result.minute == 30


def test_localtime__with_utc_datetime():
    # Test with UTC datetime - should convert to Europe/Zurich
    utc_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=pytz.UTC)
    result = d.localtime(utc_dt)
    assert result.hour == 11  # UTC+1 in winter (CET)
    assert result.minute == 30
    assert result.tzinfo is not None
    assert result.tzname() == "CET"


def test_localtime__with_utc_datetime__summer():
    # Test with UTC datetime in summer - should convert to CEST
    utc_dt = datetime(2024, 7, 15, 10, 30, 0, tzinfo=pytz.UTC)
    result = d.localtime(utc_dt)
    assert result.hour == 12  # UTC+2 in summer (CEST)
    assert result.minute == 30
    assert result.tzinfo is not None
    assert result.tzname() == "CEST"


def test_localdate__no_input():
    # Test localdate() without input returns current date
    result = d.localdate()
    assert isinstance(result, date)


def test_localdate__with_naive_datetime():
    # Test with naive datetime
    naive_dt = datetime(2024, 1, 15, 23, 30, 0)
    result = d.localdate(naive_dt)
    assert isinstance(result, date)
    # Naive 23:30 is interpreted as local time, so still Jan 15
    assert result == date(2024, 1, 15)


def test_localdate__with_utc_datetime():
    # Test with UTC datetime - should convert to Europe/Zurich date
    dt = datetime(2024, 1, 15, 23, 30, 0, tzinfo=pytz.UTC)
    result = d.localdate(dt)
    # UTC 23:30 on Jan 15 becomes 00:30 on Jan 16 in CET (UTC+1)
    assert result == date(2024, 1, 16)
