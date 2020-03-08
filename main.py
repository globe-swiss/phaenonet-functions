from phenoback.functions import activity, analytics
import firebase_admin
from phenoback.gcloud.utils import get_id, get_field

firebase_admin.initialize_app()


def process_activity(data, context):
    trigger_resource = context.resource
    print(type(context))
    print(context)
    print(data)
    print('Function triggered by change to: %s' % trigger_resource)
    activity.process_activity(get_id(context), get_field(data, 'individual'), get_field(data, 'user'))


def process_observation(data, context):
    trigger_resource = context.resource
    print(context)
    print(data)
    print('Function triggered by change to: %s' % trigger_resource)
    if len(data['value']) > 0:
        analytics.process_observation(get_id(context), get_field(data, 'date'), get_field(data, 'individual_id'),
                                      get_field(data, 'source'), get_field(data, 'year'), get_field(data, 'species'),
                                      get_field(data, 'phenophase'))
    else:
        analytics.remove_observation(get_id(context))


