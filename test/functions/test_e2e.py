import datetime

import pytest
from flask import Response
import tzlocal

from phenoback.functions import e2e
from phenoback.utils import data as d
from phenoback.utils import firestore as f


@pytest.fixture
def delete_user_data_mock(mocker):
    return mocker.patch("phenoback.functions.e2e.delete_user_data")


@pytest.fixture
def restore_test_users_mock(mocker):
    return mocker.patch("phenoback.functions.e2e.restore_test_users")


@pytest.fixture
def restore_sensor_test_data_mock(mocker):
    return mocker.patch("phenoback.functions.e2e.restore_sensor_test_data")


def test_main_reset(delete_user_data_mock):
    assert isinstance(e2e.main_reset("ignored"), Response)
    delete_user_data_mock.assert_called_once()
    delete_user_data_mock.assert_called_with(
        ["q7lgBm5nm7PUkof20UdZ9D4d0CV2", "JIcn8kFpI4fYYcbdi9QzPlrHomn1"]
    )


def test_main_restore(restore_test_users_mock, restore_sensor_test_data_mock):
    assert isinstance(e2e.main_restore("ignored"), Response)
    restore_test_users_mock.assert_called_once()
    restore_sensor_test_data_mock.assert_called_once()


def test_delete_individuals():
    d.write_individual("u1_i1", {"user": "u1"})
    d.write_individual("u1_i2", {"user": "u1"})
    d.write_individual("u2_i1", {"user": "u2"})
    d.write_individual("u2_i2", {"user": "u2"})
    d.write_individual("u3_i1", {"user": "u3"})
    d.write_individual("u3_i2", {"user": "u3"})

    e2e.delete_user_data(["u1", "u3"])
    for individual in f.collection("individuals").stream():
        assert individual.to_dict()["user"] == "u2"


def test_remove_following():
    d.write_document(
        "users",
        "u1",
        {"foo": "bar", "following_individuals": "foo", "following_users": "bar"},
    )
    d.write_document(
        "users",
        "u2",
        {"foo": "bar", "following_individuals": "foo", "following_users": "bar"},
    )
    d.write_document("users", "u3", {"foo": "bar"})

    e2e.delete_user_data(["u1", "u3"])
    results = list(f.collection("users").stream())
    assert len(results) == 3
    for user in results:
        assert user.to_dict().get("foo"), user.to_dict()
        if user.id == "u2":
            assert user.to_dict().get("following_individuals"), user.to_dict()
            assert user.to_dict().get("following_users"), user.to_dict()
        else:
            assert not user.to_dict().get("following_individuals"), user.to_dict()
            assert not user.to_dict().get("following_users"), user.to_dict()


@pytest.mark.parametrize(
    "user_id",
    [
        "q7lgBm5nm7PUkof20UdZ9D4d0CV2",
        "JIcn8kFpI4fYYcbdi9QzPlrHomn1",
        "3NOG91ip31ZdzdIjEdhaoA925U72",
    ],
)
def test_restore_test_users(user_id):
    e2e.restore_test_users()
    user = d.get_user(user_id)
    assert user, f"users document for user_id {user_id} not found"
    assert f.get_document(
        "public_users", user_id
    ), f"public_users document for user_id {user_id} not found"
    assert f.get_document(
        "nicknames", user["nickname"]
    ), f"nicknames document for nickname {user['nickname']} not found"
    assert f.get_document("public_users", user_id)["nickname"] == user["nickname"]
    assert f.get_document("nicknames", user["nickname"]) == {"user": user_id}


@pytest.mark.parametrize(
    "user_id",
    ["JIcn8kFpI4fYYcbdi9QzPlrHomn1", "3NOG91ip31ZdzdIjEdhaoA925U72"],
)
def test_restore_test_users__ranger(user_id):
    e2e.restore_test_users()
    public_user = f.get_document("public_users", user_id)
    assert public_user["roles"] == ["ranger"], public_user["roles"]


@pytest.mark.parametrize(
    "base_date,months,expected_count",
    [
        (datetime.date(2023, 1, 1), 1, 31),  # January has 31 days
        (datetime.date(2023, 2, 1), 1, 28),  # February 2023 has 28 days
        (datetime.date(2024, 2, 1), 1, 29),  # February 2024 has 29 days (leap year)
        (datetime.date(2023, 4, 1), 1, 30),  # April has 30 days
        (datetime.date(2023, 1, 1), 2, 59),  # Jan + Feb 2023 = 31 + 28
        (datetime.date(2023, 11, 1), 2, 61),  # Nov + Dec = 30 + 31
    ],
)
def test_monthdates(base_date, months, expected_count):
    result = e2e.monthdates(base_date, months)
    assert len(result) == expected_count
    assert all(isinstance(d, datetime.date) for d in result)
    assert result[0] == base_date
    # Verify dates are in sequence
    for i in range(1, len(result)):
        assert result[i] == result[i - 1] + datetime.timedelta(days=1)


@pytest.mark.parametrize(
    "year,quarter,expected_start,expected_count",
    [
        (2023, 1, datetime.date(2023, 1, 1), 90),  # Q1: Jan-Mar (31+28+31)
        (2023, 2, datetime.date(2023, 4, 1), 91),  # Q2: Apr-Jun (30+31+30)
        (2023, 3, datetime.date(2023, 7, 1), 92),  # Q3: Jul-Sep (31+31+30)
        (2023, 4, datetime.date(2023, 10, 1), 92),  # Q4: Oct-Dec (31+30+31)
        (2024, 1, datetime.date(2024, 1, 1), 91),  # Q1 leap year (31+29+31)
    ],
)
def test_quarterdates(year, quarter, expected_start, expected_count):
    result = e2e.quarterdates(year, quarter)
    assert len(result) == expected_count
    assert all(isinstance(d, datetime.date) for d in result)
    assert result[0] == expected_start


def test_generate_sensor_data():
    dates = [
        datetime.date(2023, 1, 1),
        datetime.date(2023, 1, 2),
        datetime.date(2023, 1, 3),
    ]
    n = 5
    at = 10.5
    st = 2.5
    ah = 60.0
    sh = 5.0

    result = e2e.generate_sensor_data(dates, n, at, st, ah, sh)

    assert len(result) == 3
    assert "2023-01-01" in result
    assert "2023-01-02" in result
    assert "2023-01-03" in result

    for _, data in result.items():
        assert data["n"] == n
        assert data["ats"] == at * n
        assert data["sts"] == st * n
        assert data["ahs"] == ah * n
        assert data["shs"] == sh * n


@pytest.mark.parametrize(
    "year,month,day",
    [
        (2023, 1, 1),
        (2023, 12, 31),
        (2024, 2, 29),  # leap year
        (2023, 6, 15),
    ],
)
def test_firebasedate(year, month, day):
    result = e2e.firebasedate(year, month, day)

    assert isinstance(result, datetime.datetime)
    assert result.tzinfo == tzlocal.get_localzone()
    assert result.year == year
    assert result.month == month
    assert result.day == day
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0
    assert result.microsecond == 0


def test_restore_sensor_test_data(mocker):
    update_observation_mock = mocker.patch("phenoback.utils.data.update_observation")
    update_individual_mock = mocker.patch("phenoback.utils.data.update_individual")

    # Call the function
    e2e.restore_sensor_test_data()

    # check sensor
    sensor = f.get_document("sensors", "2018_721")
    assert sensor is not None
    assert sensor["year"] == 2018
    assert "data" in sensor
    assert len(sensor["data"]) == 396

    # Check individual was updated
    assert update_individual_mock.call_count == 1

    # Check update_observation was called 12 times
    assert update_observation_mock.call_count == 12
