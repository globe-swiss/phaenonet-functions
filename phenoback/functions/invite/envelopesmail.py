import logging
import os
from datetime import datetime

from envelopes import Envelope

from phenoback.functions.invite.content import InviteMail
from phenoback.utils import data as d
from phenoback.utils import gsecrets

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def sendmail(maildef: InviteMail) -> dict:
    try:
        return _sendmail(maildef)
    except Exception:  # pylint: disable=broad-except
        log.info("Send mail failed: refreshing credentials")
        gsecrets.reset()
        return _sendmail(maildef)


def _sendmail(maildef: InviteMail) -> dict:
    return Envelope(
        from_addr=(maildef.from_mail, maildef.from_name),
        to_addr=(maildef.to_mail, maildef.to_name),
        subject=maildef.subject,
        text_body=maildef.text_body,
        html_body=maildef.html_body,
        headers={
            "reply-to": maildef.reply_to,
            "Date": d.localtime().strftime("%a, %d %b %Y %T %z"),
        },
    ).send(
        os.environ["mailer_host"],
        port=os.environ["mailer_port"],
        login=gsecrets.get_mailer_user(),
        password=gsecrets.get_mailer_pw(),
        tls=True,
    )[
        1
    ]
