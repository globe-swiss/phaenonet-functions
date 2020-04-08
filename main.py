import os
from phenoback.functions import activity, analytics, users, meteoswiss, observation, documents, thumbnails
import firebase_admin
from phenoback.gcloud.utils import *

firebase_admin.initialize_app(options={'storageBucket': os.environ.get('storageBucket')})


def process_activity_create(data, context):
    print('DEBUG: context: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    activity.process_activity(get_document_id(context), get_field(data, 'individual'), get_field(data, 'user'))


def process_observation_write(data, context):
    print('DEBUG: context: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    if is_create_event(data) or is_field_updated(data, 'date'):
        # ANALYTICS
        if get_field(data, 'phenophase') in ('BEA', 'BLA', 'BFA', 'BVA', 'FRA'):
            analytics.process_observation(get_document_id(context), get_field(data, 'date'),
                                          get_field(data, 'individual_id'), get_field(data, 'source'),
                                          get_field(data, 'year'), get_field(data, 'species'),
                                          get_field(data, 'phenophase'))
        else:
            print('INFO: No analytic values processed for phenophase %s' % get_field(data, 'phenophase'))
        # LAST OBSERVATION DATE
        observation.update_last_observation(get_field(data, 'individual_id'), get_field(data, 'phenophase'),
                                            get_field(data, 'date'))
    elif is_delete_event(data):
        analytics.process_remove_observation(get_document_id(context))
    else:
        print('DEBUG: Nothing to do.')


def process_user_write(data, context):
    print('DEBUG: context: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    user_id = get_document_id(context)
    if is_update_event(data) and is_field_updated(data, 'nickname'):
        print('DEBUG: process update nickname')
        users.process_update_nickname(user_id,
                                      get_field(data, 'nickname', old_value=True),
                                      get_field(data, 'nickname'))
    elif is_delete_event(data):
        print('DEBUG: process delete user')
        users.process_delete_user(user_id, get_field(data, 'nickname', old_value=True))
    elif is_create_event(data):
        print('DEBUG: process create user')
        users.process_new_user(user_id, get_field(data, 'nickname'))
    else:
        print('DEBUG: Nothing to do.')


def import_meteoswiss_data_publish(data, context):
    print('DEBUG: context: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    meteoswiss.process_stations()
    meteoswiss.process_observations()


def process_document_ts_write(data, context):
    print('DEBUG: context: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))

    if is_create_event(data):
        documents.update_created_document(get_collection_path(context), get_document_id(context))
    elif is_update_event(data) and not is_field_updated(data, documents.MODIFIED_KEY):
        documents.update_modified_document(get_collection_path(context), get_document_id(context))
    elif is_delete_event(data):
        print('INFO: document %s was deleted' % context.resource)
    else:
        print('DEBUG: Nothing to do.')


def create_thumbnail_finalize(data, context):
    print('DEBUG: context: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))

    thumbnails.process_new_image(data['name'])

