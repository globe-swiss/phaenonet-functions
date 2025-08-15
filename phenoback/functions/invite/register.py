import logging

import google.api_core.exceptions

from phenoback.utils import data as d
from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

INVITE_COLLECTION = "invites"
LOOKUP_COLLECTION = "invites_lookup"


def main(data, context):
    """
    Processes invite related documents if a user is created, modified or deleted.
    """
    user_id = g.get_document_id(context)
    nickname = g.get_field(
        data, "nickname", expected=False
    )  # don't warn on delete event

    if g.is_update_event(data) and g.is_field_updated(data, "nickname"):
        log.debug("update nickname on invites for user %s", user_id)
        change_nickname(user_id, str(nickname))
    elif g.is_delete_event(data):
        log.debug("delete invites for user %s", user_id)
        delete_user(user_id)
    elif g.is_create_event(data):
        log.debug("update invites for user %s", user_id)
        register_user(user_id)
    else:  # pragma: no cover
        log.debug("Nothing to do for %s", user_id)


def invite_id(user_id: str, email: str) -> str:
    return f"{user_id}_{email}"


def get_invite_ids(user_id: str) -> list[str]:
    """
    Get all invite ids that invited the given user.
    """
    email = d.get_email(user_id)
    lookup = f.get_document(LOOKUP_COLLECTION, email)
    return lookup["invites"] if lookup else []


def register_user(user_id: str) -> None:
    """
    Register the given user on all invites pointing to him.
    """
    for invite_id in get_invite_ids(user_id):
        register_user_invite(invite_id, user_id)


def register_user_invite(invite_id: str, user_id: str) -> None:
    """
    Register an user on a specific invite.
    """
    user = d.get_user(user_id)
    if not user:
        log.error("User not found %s", user_id)
    register_date = (
        user.get("created", f.SERVER_TIMESTAMP) if user else f.SERVER_TIMESTAMP
    )
    nickname = user.get("nickname", "Unknown") if user else "Unknown"
    log.info("Register user %s (%s) on invite %s", user_id, nickname, invite_id)
    try:
        f.update_document(
            INVITE_COLLECTION,
            invite_id,
            {
                "register_user": user_id,
                "register_nick": nickname,
                "register_date": register_date,
            },
        )
        invite = f.get_document(INVITE_COLLECTION, invite_id)
        assert invite
        inviter_id = invite["user"]
        d.follow_user(inviter_id, user_id)
    except google.api_core.exceptions.NotFound:
        log.warning(
            "Invite document %s does not exist, skipping registration", invite_id
        )


def change_nickname(user_id: str, nickname: str) -> None:
    for invite_id in get_invite_ids(user_id):
        log.info(
            "Change users nickname for %s to %s on invite %s",
            user_id,
            nickname,
            invite_id,
        )
        f.update_document(
            INVITE_COLLECTION,
            invite_id,
            {
                "register_nick": nickname,
            },
        )


def delete_user(user_id: str) -> None:  # pragma: no cover
    log.error("User deletion not implemented for invites - %s", user_id)
