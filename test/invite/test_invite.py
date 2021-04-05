from datetime import datetime, timezone

import pytest

from phenoback.functions.invite import invite
from phenoback.utils import firestore as f

COLLECTION = "invites"
COLLECTION_LOOKUP = "invites_lookup"

USER_ID = "some_id"


@pytest.fixture(autouse=True)
def mock_auth(mocker):
    mocker.patch("phenoback.utils.data.get_email", return_value="mymail@example.com")
    mocker.patch("phenoback.utils.data.user_exists", return_value=False)


@pytest.fixture
def new_invite():
    iid = "invite_id1"
    f.write_document(
        COLLECTION,
        iid,
        {"email": "email@example.com", "locale": "de-CH", "user": "user_id"},
    )
    return iid


@pytest.fixture
def resend_invite():
    iid = "invite_id2"
    f.write_document(
        COLLECTION,
        iid,
        {
            "email": "email@example.com",
            "locale": "de-CH",
            "user": "user_id",
            "sent": str(datetime(2021, 1, 1)),
            "resend": True,
        },
    )
    return iid


# @pytest.fixture
# def resend_invite_fail():
#     iid = "invite_id3"
#     f.write_document(
#         COLLECTION,
#         iid,
#         {
#             "email": "email@example.com",
#             "locale": "de-CH",
#             "user": "user_id",
#             "sent": str(datetime.now()),
#             "resend": True,
#         },
#     )
#     return iid


@pytest.fixture
def a_user():
    f.write_document("users", USER_ID, {"nickname": "mynickname"})
    return USER_ID


def get_invite(doc_id):
    return f.get_document(COLLECTION, doc_id)


@pytest.mark.parametrize(
    "locale, expected",
    [
        ("de-CH", "de"),
        ("fr-CH", "fr"),
        ("it-CH", "it"),
        (None, "de"),
    ],
)
def test_get_language(locale, expected):
    assert invite.get_language(locale) == expected


def test_clear_resend(resend_invite):
    assert get_invite(resend_invite)["resend"]
    invite.clear_resend(resend_invite)
    assert get_invite(resend_invite).get("resend") is None


def test_assert_update_documents__invites(resend_invite):
    email = "mymail@example.com"
    invite.update_documents(resend_invite, email)
    update_invite = get_invite(resend_invite)
    assert update_invite["sent"]
    assert update_invite["numsent"] == 1
    assert update_invite.get("resent") is None


def test_assert_update_documents__numsend(resend_invite):
    email = "mymail@example.com"
    invite.update_documents(resend_invite, email)
    invite.update_documents(resend_invite, email)
    update_invite = get_invite(resend_invite)
    assert update_invite["numsent"] == 2


def test_assert_update_documents__lookups_same(new_invite, resend_invite):
    email = "mymail@example.com"
    invite.update_documents(new_invite, email)
    invite.update_documents(resend_invite, email)
    invite_lookup = f.get_document(COLLECTION_LOOKUP, email)
    print(str(invite_lookup))
    assert set(invite_lookup["invites"]) == {new_invite, resend_invite}


def test_assert_update_documents__lookups_diff(new_invite):
    email1 = "mymail@example.com"
    email2 = "mymail@example.com"
    invite.update_documents(new_invite, email1)
    invite.update_documents(new_invite, email2)
    assert f.get_document(COLLECTION_LOOKUP, email1)["invites"] == [new_invite]
    assert f.get_document(COLLECTION_LOOKUP, email2)["invites"] == [new_invite]


def test_send_invite(mocker, a_user):
    mocker.patch("phenoback.utils.data.get_email", return_value="email@example.com")
    mailer_mock = mocker.patch(
        "phenoback.functions.invite.envelopesmail.sendmail", return_value={}
    )
    invite.send_invite("invite_id", "to_mail", "de_CH", a_user)
    mailer_mock.assert_called()


def test_process__user_exists(mocker):
    mocker.patch("phenoback.utils.data.user_exists", return_value=True)
    mocker.patch("phenoback.functions.invite.invite.clear_resend")
    assert invite.process("invite_id", "to_mail", "locale", "user_id") is False


def test_process__send_delta_fail(mocker, resend_invite):
    send_invite_mock = mocker.patch("phenoback.functions.invite.invite.send_invite")
    clear_resend_mock = mocker.patch("phenoback.functions.invite.invite.clear_resend")
    assert (
        invite.process(
            resend_invite,
            "to_mail",
            "locale",
            "user_id",
            datetime.now().replace(tzinfo=timezone.utc),
        )
        is False
    )
    send_invite_mock.assert_not_called()
    clear_resend_mock.assert_called()


def test_process__send_delta_ok(mocker, resend_invite):
    send_invite_mock = mocker.patch("phenoback.functions.invite.invite.send_invite")
    assert invite.process(
        resend_invite,
        "to_mail",
        "locale",
        "user_id",
        datetime(2021, 1, 1).replace(tzinfo=timezone.utc),
    )
    send_invite_mock.assert_called_once()


def test_process__new_invite(mocker, new_invite):
    send_invite_mock = mocker.patch("phenoback.functions.invite.invite.send_invite")
    assert invite.process(new_invite, "to_mail", "locale", "user_id", None)
    send_invite_mock.assert_called_once()
