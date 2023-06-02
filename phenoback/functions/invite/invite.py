import logging
from datetime import datetime, timezone

from phenoback.functions.invite import envelopesmail as mailer
from phenoback.functions.invite import register
from phenoback.functions.invite.content import InviteMail
from phenoback.utils import data as d
from phenoback.utils import firestore as f
from phenoback.utils import gcloud as g

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

INVITE_COLLECTION = "invites"
LOOKUP_COLLECTION = "invites_lookup"


def main(data, context):
    """
    Send email invites if invite is created or resend is set
    """
    # process if new invite or resend was changed but not deleted
    if g.is_create_event(data) or (
        g.is_field_updated(data, "resend")
        and g.get_field(data, "resend", expected=False)
    ):
        process(
            g.get_document_id(context),
            g.get_field(data, "email"),
            g.get_field(data, "locale"),
            g.get_field(data, "user"),
            g.get_field(data, "sent", expected=False),
        )


def process(
    doc_id: str, to_mail: str, locale: str, user_id: str, sent_date: datetime = None
) -> bool:
    send = False
    if d.user_exists(to_mail):
        log.info(
            "Invite %s by %s to %s: User already exists, registering",
            doc_id,
            user_id,
            to_mail,
        )
        invitee_user_id = d.get_user_id_by_email(to_mail)
        register.register_user_invite(doc_id, invitee_user_id)
    else:
        if sent_date is not None:
            delta = d.localtime() - sent_date
            if delta.total_seconds() < 600:  # resent only every 10 minutes
                log.info(
                    "Invite %s by %s to %s failed: Resend time of %i seconds to short",
                    doc_id,
                    user_id,
                    to_mail,
                    delta.total_seconds(),
                )
            else:
                send = True
        else:
            send = True

    if send:
        send_invite(doc_id, to_mail, locale, user_id)
        update_documents(doc_id, to_mail)
    else:
        clear_resend(doc_id)

    return send


def send_invite(doc_id: str, to_mail: str, locale: str, user_id: str) -> None:
    user = d.get_user(user_id)
    maildef = InviteMail(
        to_mail, d.get_email(user_id), user["nickname"], get_language(locale)
    )
    result = mailer.sendmail(maildef)
    log.info("Sent invite %s for %s to %s -> %s", doc_id, user_id, to_mail, result)


def update_documents(doc_id: str, to_mail: str) -> None:
    f.update_document(
        INVITE_COLLECTION,
        doc_id,
        {
            "sent": f.SERVER_TIMESTAMP,
            "numsent": f.Increment(1),
            "resend": f.DELETE_FIELD,
        },
    )
    f.write_document(
        LOOKUP_COLLECTION, to_mail, {"invites": f.ArrayUnion([doc_id])}, merge=True
    )


def clear_resend(doc_id: str) -> None:
    f.update_document(
        INVITE_COLLECTION,
        doc_id,
        {
            "resend": f.DELETE_FIELD,
        },
    )


def get_language(locale: str) -> str:
    return "de" if not locale else locale[0:2]
