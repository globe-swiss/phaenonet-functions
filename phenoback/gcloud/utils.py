from datetime import datetime
from typing import Union

import dateparser


def get_field(data, fieldname, old_value=False) -> Union[str, int, datetime, None]:
    value_type = 'oldValue' if old_value else 'value'
    value_dict = data[value_type].get('fields', {}).get(fieldname)
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


def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(u'Deleting doc {} => {}'.format(doc.id, doc.to_dict()))
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)
