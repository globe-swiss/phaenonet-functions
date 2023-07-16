import pytest
from flask import Response

from phenoback.functions import e2e
from phenoback.utils import data as d
from phenoback.utils import firestore as f


@pytest.fixture
def delete_user_data_mock(mocker):
    return mocker.patch("phenoback.functions.e2e.delete_user_data")


@pytest.fixture
def restore_test_users_mock(mocker):
    return mocker.patch("phenoback.functions.e2e.restore_test_users")


def test_main_reset(delete_user_data_mock):
    assert isinstance(e2e.main_reset("ignored"), Response)
    delete_user_data_mock.assert_called_once()
    delete_user_data_mock.assert_called_with(
        ["q7lgBm5nm7PUkof20UdZ9D4d0CV2", "JIcn8kFpI4fYYcbdi9QzPlrHomn1"]
    )


def test_main_restore(restore_test_users_mock):
    assert isinstance(e2e.main_restore("ignored"), Response)
    restore_test_users_mock.assert_called_once()


def test_delete_individuals():
    d.write_individual("u1_i1", {"user": "u1"})
    d.write_individual("u1_i2", {"user": "u1"})
    d.write_individual("u2_i1", {"user": "u2"})
    d.write_individual("u2_i2", {"user": "u2"})
    d.write_individual("u3_i1", {"user": "u3"})
    d.write_individual("u3_i2", {"user": "u3"})

    e2e.delete_user_data(["u1", "u3"])
    for individual in f.get_collection("individuals").stream():
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
    results = list(f.get_collection("users").stream())
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
    assert d.get_user(user_id), f"user_id {user_id} not found"


@pytest.mark.parametrize(
    "user_id",
    ["JIcn8kFpI4fYYcbdi9QzPlrHomn1", "3NOG91ip31ZdzdIjEdhaoA925U72"],
)
def test_restore_test_users__ranger(user_id):
    e2e.restore_test_users()
    public_user = f.get_document("public_users", user_id)
    assert public_user["roles"] == ["ranger"], public_user["roles"]
