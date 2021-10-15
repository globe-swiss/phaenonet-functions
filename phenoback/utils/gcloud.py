import logging
import os
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
        value = next(iter(value_dict.values()))
        value_type = next(iter(value_dict.keys()))
        if value_type == "stringValue":
            return str(value)
        elif value_type == "integerValue":
            return int(value)
        elif value_type == "timestampValue":
            return dateparser.parse(value)
        elif value_type == "booleanValue":
            return bool(value)
        else:  # pragma: no cover
            log.warning(
                "Unknown field type %s, returning str representation: %s",
                value_type,
                str(value),
            )
            return str(value)
    else:
        if expected:
            log.warning(
                "field %s not found in data %s, returning None", fieldname, str(data)
            )
        return None


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


def get_function_region() -> str:  # pragma: no cover
    return os.getenv("FUNCTION_REGION", "Unknown")


def get_app_host() -> str:
    host = os.getenv("appHost")
    if not host:
        host = f"{get_project()}.web.app"
    return host
