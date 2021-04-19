from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, select_autoescape


@dataclass
class InviteMail:
    def __init__(self, to_mail, from_mail, nickname, language) -> None:
        self.from_name = "PhaenoNet"
        self.from_mail = "info@phaenonet.ch"
        self.to_mail = to_mail
        self.to_name = None
        self.subject = subject(language)
        self.text_body = text_body(language, nickname, from_mail)
        self.html_body = None  # content.html_body(language, nickname, from_mail)


subjects = {"de": "placeholder de", "fr": "subject fr", "it": "subject it"}

env = Environment(
    loader=PackageLoader("phenoback.functions.invite", "."),
    autoescape=select_autoescape(),
)


def subject(language: str):
    return subjects[language]


def text_body(language: str, nickname: str, email: str):
    return _render(language + ".txt.j2", nickname=nickname, email=email)


def html_body(language: str, nickname: str, email: str):
    return _render(language + ".html.j2", nickname=nickname, email=email)


def _render(filename: str, **kwargs):
    return env.get_template(filename).render(kwargs)
