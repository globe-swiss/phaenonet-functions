import random
import string
from dataclasses import dataclass


@dataclass
class Doc:
    doc_id: str
    data: dict


def get_random_string(length) -> str:
    # Random string with the combination of lower and upper case
    letters = string.ascii_letters
    result_str = "".join(random.choice(letters) for i in range(length))  # nosec (B312)
    return result_str


class MockRequest:  # pylint: disable=too-few-public-methods
    def __init__(self, json_dict):
        self.json_dict = json_dict

    def get_json(self, **_):
        return self.json_dict
