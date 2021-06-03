import pytest

from phenoback.functions import users
from phenoback.utils import firestore as f


@pytest.fixture()
def user_id():
    return "user_id"


@pytest.fixture()
def nickname():
    return "nick1"


@pytest.fixture()
def nickname2():
    return "nick2"


def test_new_user(user_id, nickname):
    users.process_new_user(user_id, nickname)

    assert f.get_document("public_users", user_id).get("nickname") == nickname
    assert f.get_document("nicknames", nickname).get("user") == user_id


def test_update_nickname(user_id, nickname, nickname2):
    users.process_new_user(user_id, nickname)

    users.process_update_nickname(user_id, nickname, nickname2)

    assert f.get_document("public_users", user_id).get("nickname") == nickname2
    assert f.get_document("nicknames", nickname) is None
    assert f.get_document("nicknames", nickname2).get("user") == user_id


def test_delete_user(user_id, nickname):
    users.process_new_user(user_id, nickname)

    users.process_delete_user(user_id, nickname)

    assert f.get_document("public_users", user_id) is None
    assert f.get_document("nicknames", nickname) is None
