from unittest.mock import call

from phenoback.functions import users


def test_new_user(mocker):
    write_mock = mocker.patch("phenoback.functions.users.write_document")

    users.process_new_user("user_id", "nickname")

    assert write_mock.call_args_list == [
        call("nicknames", "nickname", {"user": "user_id"}),
        call("public_users", "user_id", {"nickname": "nickname"}),
    ]


def test_update_nickname(mocker):
    write_mock = mocker.patch("phenoback.functions.users.write_document")
    update_mock = mocker.patch("phenoback.functions.users.update_document")
    delete_mock = mocker.patch("phenoback.functions.users.delete_document")

    users.process_update_nickname("user_id", "nickname_old", "nickname_new")

    assert write_mock.call_args == call(
        "nicknames", "nickname_new", {"user": "user_id"}
    )
    assert update_mock.call_args == call(
        "public_users", "user_id", {"nickname": "nickname_new"}
    )
    assert delete_mock.call_args == call("nicknames", "nickname_old")


def test_delete_user(mocker):
    delete_mock = mocker.patch("phenoback.functions.users.delete_document")

    users.process_delete_user("user_id", "nickname")

    assert delete_mock.call_args_list == [
        call("nicknames", "nickname"),
        call("public_users", "user_id"),
    ]
