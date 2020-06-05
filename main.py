import logging
import os

from google.api_core import retry, exceptions
from google.api_core.retry import if_exception_type

from phenoback.functions import activity, analytics, users, meteoswiss, observation, documents, thumbnails
import firebase_admin

from phenoback.utils import glogging
from phenoback.utils.gcloud import get_document_id, get_field, is_create_event, is_field_updated, is_delete_event, \
    is_update_event, get_collection_path, get_fields_updated

firebase_admin.initialize_app(options={'storageBucket': os.environ.get('storageBucket')})
glogging.init()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def _setup_logging(data, context):
    glogging.log_id = context.event_id
    log.debug('context: (%s)' % str(context))
    log.debug('data: (%s)' % str(data))


@retry.Retry()
def process_activity_create(data, context):
    _setup_logging(data, context)
    log.info('Process activity %s' % get_document_id(context))
    activity.process_activity(get_document_id(context), get_field(data, 'individual'), get_field(data, 'user'))


@retry.Retry()
def process_observation_write(data, context):
    _setup_logging(data, context)
    observation_id = get_document_id(context)

    if is_create_event(data) or is_field_updated(data, 'date'):
        phenophase = get_field(data, 'phenophase')
        individual_id = get_field(data, 'individual_id')
        source = get_field(data, 'source')
        year = get_field(data, 'year')
        species = get_field(data, 'species')
        observation_date = get_field(data, 'date')
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
        log.info('Remove observation %s', observation_id)
        analytics.process_remove_observation(observation_id,
                                             get_field(data, 'individual_id', old_value=True),
                                             get_field(data, 'source', old_value=True),
                                             get_field(data, 'year', old_value=True),
                                             get_field(data, 'species', old_value=True),
                                             get_field(data, 'phenophase', old_value=True))
    else:
        log.debug('Nothing to do for %s' % observation_id)


@retry.Retry()
def process_user_write(data, context):
    _setup_logging(data, context)
    user_id = get_document_id(context)

    if is_update_event(data) and is_field_updated(data, 'nickname'):
        log.info('update nickname for %s', user_id)
        users.process_update_nickname(user_id,
                                      get_field(data, 'nickname', old_value=True),
                                      get_field(data, 'nickname'))
    elif is_delete_event(data):
        log.info('delete user %s' % user_id)
        users.process_delete_user(user_id, get_field(data, 'nickname', old_value=True))
    elif is_create_event(data):
        log.info('create user %s' % user_id)
        users.process_new_user(user_id, get_field(data, 'nickname'))
    else:
        log.debug('Nothing to do for %s' % user_id)


@retry.Retry()
def import_meteoswiss_data_publish(data, context):
    _setup_logging(data, context)
    log.info('Import meteoswiss stations')
    meteoswiss.process_stations()
    log.info('Import meteoswiss observations')
    meteoswiss.process_observations()


@retry.Retry()
def process_document_ts_write(data, context):
    _setup_logging(data, context)
    collection_path = get_collection_path(context)
    document_id = get_document_id(context)

    if is_create_event(data):
        log.info('update created ts on document %s' % context.resource)
        documents.update_created_document(collection_path, document_id)
    elif is_update_event(data) and not is_field_updated(data, documents.MODIFIED_KEY):
        log.info('update modified ts on document %s %s' % (context.resource, get_fields_updated(data)))
        documents.update_modified_document(collection_path, document_id)
    elif is_delete_event(data):
        log.info('document %s was deleted' % context.resource)
    else:
        log.debug('Nothing to do for document %s' % context.resource)


@retry.Retry(predicate=if_exception_type(exceptions.NotFound))
def create_thumbnail_finalize(data, context):
    _setup_logging(data, context)
    pathfile = data['name']

    log.info('Process thumbnail for %s' % pathfile)
    thumbnails.process_new_image(pathfile)
