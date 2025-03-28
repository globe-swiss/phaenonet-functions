import base64
import binascii
import json
import logging
import os
from datetime import datetime

import dateparser
from google.cloud.functions.context import Context

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def get_field(
    data: dict, fieldname: str, old_value: bool = False, expected=True
) -> str | int | float | datetime | bool | dict | list | None:
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


def _get_field(
    value_dict: dict,
) -> str | int | float | datetime | bool | dict | list | None:
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


def context2dict(context: Context) -> dict:
    return context.__dict__


def dict2context(context_dict) -> Context:
    return Context(
        eventId=context_dict.get("event_id"),
        timestamp=context_dict.get("timestamp"),
        eventType=context_dict.get("event_type"),
        resource=context_dict.get("resource"),
    )


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


def get_fields_updated(data: dict) -> list[str]:
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
    return os.getenv("version", "Unknown")


def get_location() -> str:  # pragma: no cover
    return os.getenv("location", "Unknown")


def get_data(pubsub_event) -> dict | None:
    try:
        data = pubsub_event["data"]
        return json.loads(base64.b64decode(data)) if data is not None else None
    except (TypeError, KeyError, binascii.Error, json.decoder.JSONDecodeError) as e:
        log.exception("invalid data for pubsub event: %s", pubsub_event, exc_info=e)
        return None
