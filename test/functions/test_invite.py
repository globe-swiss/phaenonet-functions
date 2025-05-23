# pylint: disable=protected-access, too-many-positional-arguments
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from phenoback.functions.invite import content, envelopesmail, invite, register
from phenoback.utils import data as d
from phenoback.utils import firestore as f

INVITE_COLLECTION = "invites"
LOOKUP_COLLECTION = "invites_lookup"

INVITEE_USER_ID = "invitee_user_id"
INVITEE_EMAIL = "invitee@example.com"
INVITEE_NICKNAME = "invitee"

INVITER_USER_ID = "inviter_user_id"
INVITER_EMAIL = "inviter@example.com"
INVITER_NICKNAME = "inviter"


def get_invite(doc_id):
    return f.get_document(INVITE_COLLECTION, doc_id)


@pytest.fixture
def new_invite():
    iid = "invite_id1"
    f.write_document(
        INVITE_COLLECTION,
        iid,
        {"email": INVITEE_EMAIL, "locale": "de-CH", "user": INVITER_USER_ID},
    )
    return iid


@pytest.fixture
def resend_invite():
    iid = "invite_id2"
    f.write_document(
        INVITE_COLLECTION,
        iid,
        {
            "email": INVITEE_EMAIL,
            "locale": "de-CH",
            "user": INVITER_USER_ID,
            "sent": str(datetime(2021, 1, 1)),
            "resend": 1,
        },
    )
    return iid


@pytest.fixture
def inviter_user():
    f.write_document(
        "users",
        INVITER_USER_ID,
        {"nickname": INVITER_NICKNAME, "created": datetime(2020, 1, 1)},
    )
    return INVITER_USER_ID


@pytest.fixture
def invitee_user():
    f.write_document(
        "users",
        INVITEE_USER_ID,
        {"nickname": INVITEE_NICKNAME, "created": datetime(2021, 1, 1)},
    )
    return INVITEE_USER_ID


class TestInvite:
    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                {
                    "updateMask": {},
                    "oldValue": {},
                    "value": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                        }
                    },
                },
                True,
            ),
            (
                {
                    "updateMask": {"fieldPaths": ["resend"]},
                    "oldValue": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                        }
                    },
                    "value": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                            "resend": {"numberValue": 1},
                        }
                    },
                },
                True,
            ),
            (
                {
                    "updateMask": {"fieldPaths": ["resend"]},
                    "oldValue": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                            "resend": {"numberValue": 1},
                        }
                    },
                    "value": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                        }
                    },
                },
                False,
            ),
            (
                {
                    "updateMask": {},
                    "oldValue": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                        }
                    },
                    "value": {},
                },
                False,
            ),
        ],
    )
    def test_process_invite_sending(self, mocker, data, expected, context):
        invite_mock = mocker.patch("phenoback.functions.invite.invite.process")
        invite.main(data, context)
        assert invite_mock.called == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                {
                    "updateMask": {"fieldPaths": ["resend"]},
                    "oldValue": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                            "sent": {"timestampValue": str(datetime(2021, 1, 1))},
                        }
                    },
                    "value": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                            "sent": {"timestampValue": str(datetime(2021, 1, 1))},
                            "resend": {"numberValue": 1},
                        }
                    },
                },
                datetime(2021, 1, 1),
            ),
            (
                {
                    "updateMask": {"fieldPaths": ["resend"]},
                    "oldValue": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                        }
                    },
                    "value": {
                        "fields": {
                            "email": {"stringValue": "email@example.com"},
                            "user": {"stringValue": "user_id"},
                            "locale": {"stringValue": "locale"},
                            "resend": {"numberValue": 1},
                        }
                    },
                },
                None,
            ),
        ],
    )
    def test_process_invite_sent(self, mocker, data, expected, context):
        invite_mock = mocker.patch("phenoback.functions.invite.invite.process")
        invite.main(data, context)
        invite_mock.assert_called()
        assert invite_mock.call_args[0][4] == expected

    @pytest.fixture(autouse=True)
    def mock_auth(self, mocker):
        mocker.patch("phenoback.utils.data.get_email", return_value=INVITEE_EMAIL)
        mocker.patch("phenoback.utils.data.user_exists", return_value=False)

    @pytest.mark.parametrize(
        "locale, expected",
        [
            ("de-CH", "de"),
            ("fr-CH", "fr"),
            ("it-CH", "it"),
            (None, "de"),
        ],
    )
    def test_get_language(self, locale, expected):
        assert invite.get_language(locale) == expected

    def test_clear_resend(self, resend_invite):  # noqa: F811
        assert get_invite(resend_invite)["resend"]
        invite.clear_resend(resend_invite)
        assert get_invite(resend_invite).get("resend") is None

    def test_assert_update_documents__invites(self, resend_invite):
        invite.update_documents(resend_invite, INVITEE_EMAIL)
        update_invite = get_invite(resend_invite)
        assert update_invite["sent"]
        assert update_invite["numsent"] == 1
        assert update_invite.get("resent") is None

    def test_assert_update_documents__numsend(self, resend_invite):
        invite.update_documents(resend_invite, INVITEE_EMAIL)
        invite.update_documents(resend_invite, INVITEE_EMAIL)
        update_invite = get_invite(resend_invite)
        assert update_invite["numsent"] == 2

    def test_assert_update_documents__lookups_same(self, new_invite, resend_invite):
        invite.update_documents(new_invite, INVITEE_EMAIL)
        invite.update_documents(resend_invite, INVITEE_EMAIL)
        invite_lookup = f.get_document(LOOKUP_COLLECTION, INVITEE_EMAIL)
        assert set(invite_lookup["invites"]) == {new_invite, resend_invite}

    def test_assert_update_documents__lookups_diff(self, new_invite):
        email1 = "1@example.com"
        email2 = "2@example.com"
        invite.update_documents(new_invite, email1)
        invite.update_documents(new_invite, email2)
        assert f.get_document(LOOKUP_COLLECTION, email1)["invites"] == [new_invite]
        assert f.get_document(LOOKUP_COLLECTION, email2)["invites"] == [new_invite]

    def test_send_invite(self, mocker, inviter_user):
        mailer_mock = mocker.patch(
            "phenoback.functions.invite.envelopesmail.sendmail", return_value={}
        )
        invite.send_invite("invite_id", INVITEE_EMAIL, "de_CH", inviter_user)
        mailer_mock.assert_called()

    def test_process__user_exists(self, mocker, new_invite):
        mocker.patch("phenoback.utils.data.user_exists", return_value=True)
        get_user_id_by_email_mock = mocker.patch(
            "phenoback.utils.data.get_user_id_by_email",
            return_value=INVITEE_USER_ID,
            autospec=True,
        )
        mocker.patch("phenoback.functions.invite.invite.clear_resend")
        register_user_invite_mock = mocker.patch(
            "phenoback.functions.invite.register.register_user_invite", autospec=True
        )

        assert not invite.process(new_invite, INVITEE_EMAIL, "locale", INVITER_USER_ID)
        get_user_id_by_email_mock.assert_called_once_with(INVITEE_EMAIL)
        register_user_invite_mock.assert_called_once_with(new_invite, INVITEE_USER_ID)

    def test_process__send_delta_fail(self, mocker, resend_invite):
        send_invite_mock = mocker.patch("phenoback.functions.invite.invite.send_invite")
        clear_resend_mock = mocker.patch(
            "phenoback.functions.invite.invite.clear_resend"
        )
        assert (
            invite.process(
                resend_invite,
                INVITEE_EMAIL,
                "locale",
                INVITER_USER_ID,
                datetime.now().replace(tzinfo=timezone.utc),
            )
            is False
        )
        send_invite_mock.assert_not_called()
        clear_resend_mock.assert_called()

    def test_process__send_delta_ok(self, mocker, resend_invite):
        send_invite_mock = mocker.patch("phenoback.functions.invite.invite.send_invite")
        assert invite.process(
            resend_invite,
            INVITEE_EMAIL,
            "locale",
            INVITER_USER_ID,
            datetime(2021, 1, 1).replace(tzinfo=timezone.utc),
        )
        send_invite_mock.assert_called_once()

    def test_process__new_invite(self, mocker, new_invite):
        send_invite_mock = mocker.patch("phenoback.functions.invite.invite.send_invite")
        assert invite.process(
            new_invite, INVITEE_EMAIL, "locale", INVITER_USER_ID, None
        )
        send_invite_mock.assert_called_once()


class TestRegister:
    @pytest.mark.skip(reason="todo: refactor context and data handling -> helpers")
    def test_main(self):
        pass

    @pytest.fixture()
    def lookup(self):
        invite_id = "invite_1"
        f.write_document(LOOKUP_COLLECTION, INVITEE_EMAIL, {"invites": [invite_id]})
        return invite_id

    @pytest.fixture()
    def lookups(self):
        invite_ids = {"invite_1", "invite_2"}
        f.write_document(LOOKUP_COLLECTION, INVITEE_EMAIL, {"invites": invite_ids})
        return invite_ids

    def test_invite_id(self):
        assert register.invite_id("user", "mail") == "user_mail"

    def test_get_invite_ids__multiple(self, mocker, lookups):
        mocker.patch("phenoback.utils.data.get_email", return_value=INVITEE_EMAIL)
        assert set(register.get_invite_ids(INVITEE_USER_ID)) == lookups

    def test_get_invite_ids__not_found(self, mocker):
        mocker.patch("phenoback.utils.data.get_email", return_value=INVITEE_EMAIL)
        assert set(register.get_invite_ids(INVITEE_USER_ID)) == set()

    def test_get_invite_ids__no_invites(self, mocker):
        mocker.patch("phenoback.utils.data.get_email", return_value=INVITEE_EMAIL)
        assert set(register.get_invite_ids(INVITEE_USER_ID)) == set()

    def test_register_user(
        self, caperrors, mocker, new_invite, inviter_user, invitee_user
    ):
        get_invites_mock = mocker.patch(
            "phenoback.functions.invite.register.get_invite_ids",
            return_value=[new_invite],
        )
        register.register_user(invitee_user)

        get_invites_mock.assert_called_once_with(INVITEE_USER_ID)
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_user")
            == INVITEE_USER_ID
        )
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_nick")
            == INVITEE_NICKNAME
        )
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_date")
            is not None
        )
        assert INVITEE_USER_ID in d.get_user(inviter_user).get("following_users")
        assert len(caperrors.records) == 0, caperrors.records

    def test_register_user__no_created(
        self, mocker, new_invite, inviter_user, invitee_user
    ):
        """
        Assert invite is registerd even if the invitee user document has no created-date.  Assert an error os logged.
        """
        f.update_document("users", invitee_user, {"created": f.DELETE_FIELD})
        get_invites_mock = mocker.patch(
            "phenoback.functions.invite.register.get_invite_ids",
            return_value=[new_invite],
        )
        register.register_user(invitee_user)

        get_invites_mock.assert_called_once_with(INVITEE_USER_ID)
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_user")
            == INVITEE_USER_ID
        )
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_nick")
            is not None
        )
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_date")
            is not None
        )
        assert INVITEE_USER_ID in d.get_user(inviter_user).get("following_users")

    def test_register_user__invitee_user_not_found(
        self, caperrors, mocker, new_invite, inviter_user
    ):
        """
        Assert invite is registerd even if the invitee user document is not present. Assert an error os logged.
        """
        get_invites_mock = mocker.patch(
            "phenoback.functions.invite.register.get_invite_ids",
            return_value=[new_invite],
        )
        register.register_user(INVITEE_USER_ID)

        get_invites_mock.assert_called_once_with(INVITEE_USER_ID)
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_user")
            == INVITEE_USER_ID
        )
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_nick")
            is not None
        )
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_date")
            is not None
        )
        assert INVITEE_USER_ID in d.get_user(inviter_user).get("following_users")
        assert len(caperrors.records) == 1, caperrors.records

    def test_change_nickname(self, mocker, new_invite):
        new_nickname = "a_new_nickname"
        get_invites_mock = mocker.patch(
            "phenoback.functions.invite.register.get_invite_ids",
            return_value=[new_invite],
        )
        assert get_invite(new_invite).get("nickname") != new_nickname

        register.change_nickname(INVITEE_USER_ID, new_nickname)

        get_invites_mock.assert_called_once_with(INVITEE_USER_ID)
        assert (
            f.get_document(INVITE_COLLECTION, new_invite).get("register_nick")
            == new_nickname
        )


class TestMail:
    @pytest.fixture(autouse=True)
    def env(self, mocker):
        mocker.patch("phenoback.utils.gsecrets.get_mailer_pw")
        mocker.patch("phenoback.utils.gsecrets.get_mailer_user")
        os.environ["mailer_host"] = "host"
        os.environ["mailer_port"] = "1111"

    @pytest.fixture()
    def invite_mail(self):
        return MagicMock().create_autospec(content.InviteMail)

    def test__sendmail(self, mocker, invite_mail):
        send_mock = mocker.patch(
            "envelopes.Envelope.send", return_value=["ignored", "return_value"]
        )
        assert envelopesmail._sendmail(invite_mail) == "return_value"
        send_mock.assert_called()

    def test_sendmail__good_credentials(self, mocker, invite_mail):
        send_mock = mocker.patch(
            "phenoback.functions.invite.envelopesmail._sendmail",
            return_value={},
        )
        reset_mock = mocker.patch("phenoback.utils.gsecrets.reset")
        # explicit test for empty dict
        assert envelopesmail.sendmail(invite_mail) == {}  # pylint: disable=C1803
        assert send_mock.call_count == 1
        reset_mock.assert_not_called()

    def test_sendmail__refresh_credentials(self, mocker, invite_mail):
        send_mock = mocker.patch(
            "phenoback.functions.invite.envelopesmail._sendmail",
            side_effect=[Exception("invalid credentials"), {}],
        )
        reset_mock = mocker.patch("phenoback.utils.gsecrets.reset")
        # explicit test for empty dict
        assert envelopesmail.sendmail(invite_mail) == {}  # pylint: disable=C1803
        assert send_mock.call_count == 2
        reset_mock.assert_called_once()

    def test_sendmail__refresh_credentials_failed(self, mocker, invite_mail):
        send_mock = mocker.patch(
            "phenoback.functions.invite.envelopesmail._sendmail",
            side_effect=[
                Exception("invalid credentials"),
                Exception("invalid credentials"),
            ],
        )
        reset_mock = mocker.patch("phenoback.utils.gsecrets.reset")
        with pytest.raises(Exception):
            envelopesmail.sendmail(invite_mail)
        assert send_mock.call_count == 2
        reset_mock.assert_called_once()


class TestContent:
    @pytest.fixture(params=["de", "fr", "it"])
    def language(self, request):
        return request.param

    def test_subject(self, language):
        assert content.subject(language) is not None

    def test_text_body(self, language):
        nick = "mynickname"
        email = "myemail"
        body = content.text_body(language, nick, email)
        assert nick in body
        assert email in body

    def test_html_body(self, language, gcp_project):
        nick = "mynickname"
        email = "myemail"
        body = content.html_body(language, nick, email)
        assert nick in body
        assert email in body
        assert f"https://{gcp_project}.web.app/assets/" in body  # check url
