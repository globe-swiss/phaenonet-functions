from datetime import datetime
from typing import Union

import dateparser


def get_field(data, fieldname) -> Union[str, int, datetime, None]:
    value_dict = data['value']['fields'].get(fieldname)
    if value_dict:
        value = next(iter(value_dict.values()))
        value_type = next(iter(value_dict.keys()))
        if value_type == 'stringValue':
            return str(value)
        elif value_type == 'integerValue':
            return int(value)
        elif value_type == 'timestampValue':
            return dateparser.parse(value)
        else:
            print("WARN: Unknown field type %s, returning str representation: %s" % (value_type, str(value)))
            return str(value)
    else:
        print("WARN: field %s not found in data %s" % (fieldname, str(data)))


def get_id(function_context) -> str:
    return function_context.resource.split('/')[-1]