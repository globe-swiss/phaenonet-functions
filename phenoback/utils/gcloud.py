import base64
import json
import logging
import os
from collections import namedtuple
from datetime import datetime
from typing import List, Union

import dateparser

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def get_field(
    data: dict, fieldname: str, old_value: bool = False, expected=True
) -> Union[str, int, datetime, None]:
    value_type = "oldValue" if old_value else "value"
    value_dict = data[value_type].get("fields", {}).get(fieldname)
    if value_dict is not None:
        return _get_field(value_dict)
    else:
        if expected:
            log.warning(
                "field %s not found in data %s, returning None", fieldname, str(data)
            )
        return None


def _get_field(value_dict: dict):
    value = next(iter(value_dict.values()))
    value_type = next(iter(value_dict.keys()))
    if value_type == "stringValue":
        return str(value)
    elif value_type == "integerValue":
        return int(value)
    elif value_type == "doubleValue":
        return float(value)
    elif value_type == "timestampValue":
        return dateparser.parse(value)
    elif value_type == "booleanValue":
        return bool(value)
    elif value_type == "mapValue":
        return dict(
            zip(
                value["fields"].keys(),
                [_get_field(v) for v in value["fields"].values()],
            )
        )
    elif value_type == "arrayValue":
        return [_get_field(v) for v in value["values"]]
    else:
        log.error(
            "Unknown field type %s, returning str representation: %s",
            value_type,
            str(value),
        )
        return str(value)


def context2dict(context) -> dict:
    return context._asdict()


def dict2context(context_dict) -> namedtuple:
    return namedtuple("context", context_dict.keys())(**context_dict)


def get_document_id(context) -> str:
    return context.resource.split("/")[-1]


def get_collection_path(context) -> str:
    return "/".join(context.resource.split("/")[5:-1])


def is_create_event(data: dict) -> bool:
    return len(data["value"]) > 0 and len(data["oldValue"]) == 0


def is_update_event(data: dict) -> bool:
    return len(data["value"]) > 0 and len(data["oldValue"]) > 0


def is_delete_event(data: dict) -> bool:
    return len(data["value"]) == 0 and len(data["oldValue"]) > 0


def is_field_updated(data: dict, fieldname) -> bool:
    return fieldname in get_fields_updated(data)


def get_fields_updated(data: dict) -> List[str]:
    return data.get("updateMask", {}).get("fieldPaths", [])


def get_function_name() -> str:  # pragma: no cover
    return os.getenv("FUNCTION_TARGET", "Unknown")


def get_project() -> str:  # pragma: no cover
    return os.getenv("GCP_PROJECT", "Unknown")


def get_app_host() -> str:
    host = os.getenv("appHost")
    if not host:
        host = f"{get_project()}.web.app"
    return host


def get_version() -> str:  # pragma: no cover
    return os.getenv("version")


def get_location() -> str:  # pragma: no cover
    return os.getenv("location")


def get_data(pubsub_event):
    data = base64.b64decode(pubsub_event["data"])
    return json.loads(data)
