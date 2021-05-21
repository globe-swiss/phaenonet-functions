from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, select_autoescape

from phenoback.utils import gcloud


@dataclass
class InviteMail:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, to_mail, from_mail, nickname, language) -> None:
        self.from_name = "PhaenoNet"
        self.from_mail = "no-reply@phaenonet.ch"
        self.reply_to = "info@phaenonet.ch"
        self.to_mail = to_mail
        self.to_name = None
        self.subject = subject(language)
        self.text_body = text_body(language, nickname, from_mail)
        self.html_body = html_body(language, nickname, from_mail)


subjects = {
    "de": "Einladung zu PhaenoNet",
    "fr": "Invitation à rejoindre PhaenoNet",
    "it": "Invito a PhaenoNet",
}

env = Environment(
    loader=PackageLoader("phenoback.functions.invite", "."),
    autoescape=select_autoescape(),
)


def subject(language: str):
    return subjects[language]


def text_body(language: str, nickname: str, email: str):
    return _render(language + ".txt.j2", nickname=nickname, email=email)


def html_body(language: str, nickname: str, email: str):
    return _render(
        language + ".html.j2",
        nickname=nickname,
        email=email,
        url="https://%s" % gcloud.get_app_host(),
    )


def _render(filename: str, **kwargs):
    return env.get_template(filename).render(kwargs)
