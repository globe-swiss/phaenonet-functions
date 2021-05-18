import logging
from typing import List

from phenoback.utils import data as d
from phenoback.utils import firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

INVITE_COLLECTION = "invites"
LOOKUP_COLLECTION = "invites_lookup"


def invite_id(user_id: str, email: str) -> str:
    return "%s_%s" % (user_id, email)


def get_invite_ids(user_id: str) -> List[str]:
    """
    Get all invite ids that invited the given user.
    """
    email = d.get_email(user_id)
    lookup = f.get_document(LOOKUP_COLLECTION, email)
    return lookup["invites"] if lookup else []


def register_user(user_id: str, nickname: str) -> None:
    """
    Register the given user on all invites pointing to him.
    """
    for invite_id in get_invite_ids(user_id):
        register_user_invite(invite_id, user_id, nickname)


def register_user_invite(invite_id: str, user_id: str, nickname: str) -> None:
    """
    Register an user on a specific invite.
    """
    log.info("Register user %s (%s) on invite %s", user_id, nickname, invite_id)
    f.update_document(
        INVITE_COLLECTION,
        invite_id,
        {
            "register_user": user_id,
            "register_nick": nickname,
            "register_date": f.SERVER_TIMESTAMP,
        },
    )
    inviter_id = f.get_document(INVITE_COLLECTION, invite_id)["user"]
    d.follow_user(inviter_id, user_id)


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
