from phenoback.functions import activity
import firebase_admin

firebase_admin.initialize_app()


def process_activity(data, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
        data (dict): Event payload.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    trigger_resource = context.resource
    print(context)
    print(data)
    print('Function triggered by change to: %s' % trigger_resource)
    activity.process_activity(trigger_resource.split('/')[-1],
                              data['value']['fields']['individual']['stringValue'],
                              data['value']['fields']['user']['stringValue'])
