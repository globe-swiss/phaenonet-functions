import logging
import os
from contextlib import contextmanager

import firebase_admin
from google.api_core import exceptions, retry
from google.api_core.retry import if_exception_type

from phenoback.utils import glogging
from phenoback.utils.gcloud import (
    get_collection_path,
    get_document_id,
    get_field,
    get_fields_updated,
    is_create_event,
    is_delete_event,
    is_field_updated,
    is_update_event,
)

# allow import outside toplevel as not all modules need to be loaded for every function
# pylint: disable=import-outside-toplevel

firebase_admin.initialize_app(
    options={"storageBucket": os.environ.get("storageBucket")}
)
glogging.init()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

ANALYTIC_PHENOPHASES = ("BEA", "BLA", "BFA", "BVA", "FRA")


@contextmanager  # workaround as stackdriver fails to capture stackstraces
def setup(data, context):
    try:
        glogging.log_id = str(context.event_id)
        log.debug("context: (%s)", str(context))
        log.debug("data: (%s)", str(data))
        yield
    except Exception:
        log.exception("Fatal error in cloud function")
        raise


def _process_observation_activity(data, context, action):
    from phenoback.functions import activity

    delete_op = action == "delete"
    activity.process_observation(
        event_id=context.event_id,
        observation_id=get_document_id(context),
        individual_id=get_field(data, "individual_id", old_value=delete_op),
        user_id=get_field(data, "user", old_value=delete_op),
        phenophase=get_field(data, "phenophase", old_value=delete_op),
        source=get_field(data, "source", old_value=delete_op),
        species=get_field(data, "species", old_value=delete_op),
        individual=get_field(data, "individual", old_value=delete_op),
        action=action,
    )


@retry.Retry()
def process_observation_write_activity(data, context):
    """
    Creates an activity when an observation is created, modified or deleted in
    Firestore **and** the user or individual of that observation is being followed.
    """
    with setup(data, context):
        observation_id = get_document_id(context)
        if is_create_event(data):
            log.info("Add create activity for observation %s", observation_id)
            _process_observation_activity(data, context, "create")
        elif is_field_updated(data, "date"):
            log.info("Add modify activity for observation %s", observation_id)
            _process_observation_activity(data, context, "modify")
        elif is_delete_event(data):
            log.info("Add delete activity for observation %s", observation_id)
            _process_observation_activity(data, context, "delete")
        else:
            log.debug("No activity to add")


@retry.Retry()
def process_observation_create_analytics(data, context):
    """
    Updates analytic values in Firestore when an observation is created in Firestore.
    """
    with setup(data, context):
        from phenoback.functions import observation

        observation_id = get_document_id(context)
        phenophase = get_field(data, "phenophase")
        individual_id = get_field(data, "individual_id")
        source = get_field(data, "source")
        year = get_field(data, "year")
        species = get_field(data, "species")
        observation_date = get_field(data, "date")

        if phenophase in ANALYTIC_PHENOPHASES:
            from phenoback.functions import analytics

            log.info(
                "Process analytic values for %s, phenophase %s",
                observation_id,
                phenophase,
            )
            analytics.process_observation(
                observation_id,
                observation_date,
                individual_id,
                source,
                year,
                species,
                phenophase,
            )
        else:
            log.debug(
                "No analytic values processed for %s, phenophase %s",
                observation_id,
                phenophase,
            )
        # LAST OBSERVATION DATE
        log.info(
            "Process last observation date for %s, phenophase %s",
            observation_id,
            phenophase,
        )
        observation.update_last_observation(individual_id, phenophase, observation_date)


@retry.Retry()
def process_observation_update_analytics(data, context):
    """
    Updates analytical values in Firestore if the observation date was modified on a observation document.
    """
    with setup(data, context):
        if is_field_updated(data, "date"):
            process_observation_create_analytics(data, context)


@retry.Retry()
def process_observation_delete_analytics(data, context):
    """
    Updates analytical values in Firestore if an observation was deleted.
    """
    with setup(data, context):
        observation_id = get_document_id(context)
        phenophase = get_field(data, "phenophase", old_value=True)
        if phenophase in ANALYTIC_PHENOPHASES:
            from phenoback.functions import analytics

            log.info("Remove observation %s", observation_id)
            analytics.process_remove_observation(
                observation_id,
                get_field(data, "individual_id", old_value=True),
                get_field(data, "source", old_value=True),
                get_field(data, "year", old_value=True),
                get_field(data, "species", old_value=True),
                phenophase,
            )
        else:
            log.debug(
                "No analytic values processed for %s, phenophase %s",
                observation_id,
                phenophase,
            )


@retry.Retry()
def process_user_write(data, context):
    """
    Processes user related documents if a user is created, modified or deleted.
    """
    with setup(data, context):
        from phenoback.functions import users

        user_id = get_document_id(context)

        if is_update_event(data) and is_field_updated(data, "nickname"):
            log.info("update nickname for %s", user_id)
            users.process_update_nickname(
                user_id,
                get_field(data, "nickname", old_value=True),
                get_field(data, "nickname"),
            )
        elif is_delete_event(data):
            log.info("delete user %s", user_id)
            users.process_delete_user(
                user_id, get_field(data, "nickname", old_value=True)
            )
        elif is_create_event(data):
            log.info("create user %s", user_id)
            users.process_new_user(user_id, get_field(data, "nickname"))
        else:
            log.debug("Nothing to do for %s", user_id)


@retry.Retry()
def import_meteoswiss_data_publish(data, context):
    """
    Imports meteoswiss stations and observations.
    """
    with setup(data, context):
        from phenoback.functions import meteoswiss

        log.info("Import meteoswiss stations")
        meteoswiss.process_stations()
        log.info("Import meteoswiss observations")
        meteoswiss.process_observations()


@retry.Retry()
def process_document_ts_write(data, context):
    """
    Updates create and modified timestamps on documents.
    """
    with setup(data, context):
        from phenoback.functions import documents

        collection_path = get_collection_path(context)
        document_id = get_document_id(context)

        if is_create_event(data):
            log.info("update created ts on document %s", context.resource)
            documents.update_created_document(collection_path, document_id)
        elif is_update_event(data) and not is_field_updated(
            data, documents.MODIFIED_KEY
        ):
            log.info(
                "update modified ts on document %s %s",
                context.resource,
                get_fields_updated(data),
            )
            documents.update_modified_document(collection_path, document_id)
        elif is_delete_event(data):
            log.info("document %s was deleted", context.resource)
        else:
            log.debug("Nothing to do for document %s", context.resource)


@retry.Retry(predicate=if_exception_type(exceptions.NotFound))
def create_thumbnail_finalize(data, context):
    """
    Creates thumbnails for images uploaded to google cloud storage.
    """
    with setup(data, context):
        from phenoback.functions import thumbnails

        pathfile = data["name"]

        log.info("Process thumbnail for %s", pathfile)
        thumbnails.process_new_image(pathfile)


@retry.Retry()
def rollover_manual(data, context):
    """
    Rollover the phenoyear. Rollover is based on the year defined in the dynamic configuration definition in firestore.
    """
    with setup(data, context):
        from phenoback.functions import rollover

        rollover.rollover()


@retry.Retry()
def e2e_clear_user_individuals_http(request):
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    import time
    from collections import namedtuple

    Context = namedtuple("context", "event_id")
    context = Context(event_id=time.time())

    with setup(request, context):
        from phenoback.functions import e2e

        e2e.delete_user_individuals("q7lgBm5nm7PUkof20UdZ9D4d0CV2")
