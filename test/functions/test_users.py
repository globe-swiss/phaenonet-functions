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


def test_main__create(mocker, data, context, user_id, nickname):
    mocker.patch("phenoback.utils.gcloud.is_create_event", return_value=True)
    mocker.patch("phenoback.utils.gcloud.is_update_event", return_value=False)
    mocker.patch("phenoback.utils.gcloud.is_delete_event", return_value=False)
    get_field_mock = mocker.patch(
        "phenoback.utils.gcloud.get_field", return_value=nickname
    )
    mocker.patch("phenoback.utils.gcloud.get_document_id", return_value=user_id)
    process_create_mock = mocker.patch("phenoback.functions.users.process_new_user")

    users.main(data, context)

    get_field_mock.assert_called_once_with(data, "nickname")
    process_create_mock.assert_called_once_with(user_id, nickname)


def test_main__update(mocker, data, context, user_id, nickname, nickname2):
    mocker.patch("phenoback.utils.gcloud.is_create_event", return_value=False)
    mocker.patch("phenoback.utils.gcloud.is_update_event", return_value=True)
    mocker.patch("phenoback.utils.gcloud.is_delete_event", return_value=False)
    is_field_updated_mock = mocker.patch(
        "phenoback.utils.gcloud.is_field_updated", return_value=True
    )
    get_field_mock = mocker.patch(
        "phenoback.utils.gcloud.get_field", side_effect=[nickname, nickname2]
    )
    mocker.patch("phenoback.utils.gcloud.get_document_id", return_value=user_id)
    process_update_mock = mocker.patch(
        "phenoback.functions.users.process_update_nickname"
    )

    users.main(data, context)

    get_field_mock.assert_has_calls(
        [mocker.call(data, "nickname"), mocker.call(data, "nickname", old_value=True)],
        any_order=True,
    )
    is_field_updated_mock.assert_called_once_with(data, "nickname")
    process_update_mock.assert_called_once_with(user_id, nickname, nickname2)


def test_main__no_update(mocker, data, context, user_id):
    mocker.patch("phenoback.utils.gcloud.is_create_event", return_value=False)
    mocker.patch("phenoback.utils.gcloud.is_update_event", return_value=True)
    mocker.patch("phenoback.utils.gcloud.is_delete_event", return_value=False)
    is_field_updated_mock = mocker.patch(
        "phenoback.utils.gcloud.is_field_updated", return_value=False
    )
    mocker.patch("phenoback.utils.gcloud.get_document_id", return_value=user_id)
    process_update_mock = mocker.patch(
        "phenoback.functions.users.process_update_nickname"
    )

    users.main(data, context)

    is_field_updated_mock.assert_called_once_with(data, "nickname")
    process_update_mock.assert_not_called()


def test_main__delete(mocker, data, context, user_id, nickname):
    mocker.patch("phenoback.utils.gcloud.is_create_event", return_value=False)
    mocker.patch("phenoback.utils.gcloud.is_update_event", return_value=False)
    mocker.patch("phenoback.utils.gcloud.is_delete_event", return_value=True)
    get_field_mock = mocker.patch(
        "phenoback.utils.gcloud.get_field", return_value=nickname
    )
    mocker.patch("phenoback.utils.gcloud.get_document_id", return_value=user_id)
    process_delete_mock = mocker.patch("phenoback.functions.users.process_delete_user")

    users.main(data, context)

    get_field_mock.assert_called_once_with(data, "nickname", old_value=True)
    process_delete_mock.assert_called_once_with(user_id, nickname)


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
