import logging
import os

from google.api_core import retry, exceptions
from google.api_core.retry import if_exception_type

from phenoback.functions import activity, analytics, users, meteoswiss, observation, documents, thumbnails
import firebase_admin

from phenoback.gcloud import glogging
from phenoback.gcloud.utils import get_document_id, get_field, is_create_event, is_field_updated, is_delete_event, \
    is_update_event, get_collection_path

firebase_admin.initialize_app(options={'storageBucket': os.environ.get('storageBucket')})
glogging.init()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def process_activity_create(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))

    log.info('Process activity %s' % get_document_id(context))
    activity.process_activity(get_document_id(context), get_field(data, 'individual'), get_field(data, 'user'))


def process_observation_write(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))

    observation_id = get_document_id(context)
    phenophase = get_field(data, 'phenophase')
    individual_id = get_field(data, 'individual_id')
    source = get_field(data, 'source')
    year = get_field(data, 'year')
    species = get_field(data, 'species')
    observation_date = get_field(data, 'date')

    if is_create_event(data) or is_field_updated(data, 'date'):
        # ANALYTICS
        if phenophase in ('BEA', 'BLA', 'BFA', 'BVA', 'FRA'):
            log.info('Process analytic values for %s, phenophase %s' % (observation_id, phenophase))
            analytics.process_observation(observation_id, observation_date, individual_id, source, year, species,
                                          phenophase)
        else:
            log.info('No analytic values processed for %s, phenophase %s' % (observation_id, phenophase))
        # LAST OBSERVATION DATE
        log.info('Process last observation date for %s, phenophase %s' % (observation_id, phenophase))
        observation.update_last_observation(individual_id, phenophase, observation_date)
    elif is_delete_event(data):
        log.info('Delete observation %s, phenophase %s')
        analytics.process_remove_observation(observation_id)
    else:
        log.debug('Nothing to do for %s, phenophase %s' % (observation_id, phenophase))


def process_user_write(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))

    user_id = get_document_id(context)
    nickname_old = get_field(data, 'nickname', old_value=True)
    nickname_new = get_field(data, 'nickname')

    if is_update_event(data) and is_field_updated(data, 'nickname'):
        log.info('update nickname for %s', user_id)
        users.process_update_nickname(user_id, nickname_old, nickname_new)
    elif is_delete_event(data):
        log.info('delete user %s' % user_id)
        users.process_delete_user(user_id, nickname_old)
    elif is_create_event(data):
        log.info('create user %s' % user_id)
        users.process_new_user(user_id, nickname_new)
    else:
        log.debug('Nothing to do for %s' % user_id)


def import_meteoswiss_data_publish(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))

    log.info('Import meteoswiss stations')
    meteoswiss.process_stations()
    log.info('Import meteoswiss observations')
    meteoswiss.process_observations()


def process_document_ts_write(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))

    collection_path = get_collection_path(context)
    document_id = get_document_id(context)

    if is_create_event(data):
        log.info('update created ts on document %s' % context.resource)
        documents.update_created_document(collection_path, document_id)
    elif is_update_event(data) and not is_field_updated(data, documents.MODIFIED_KEY):
        log.info('update modified ts on document %s' % context.resource)
        documents.update_modified_document(collection_path, document_id)
    elif is_delete_event(data):
        log.info('document %s was deleted' % context.resource)
    else:
        log.debug('Nothing to do for document %s' % context.resource)


@retry.Retry(predicate=if_exception_type(exceptions.NotFound))
def create_thumbnail_finalize(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))

    pathfile = data['name']

    log.info('Process thumbnail for %s' % pathfile)
    thumbnails.process_new_image(pathfile)
