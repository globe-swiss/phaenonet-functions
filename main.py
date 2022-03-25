# allow import outside toplevel as not all modules need to be loaded for every function
# pylint: disable=import-outside-toplevel
import logging
import os
import time
from contextlib import contextmanager
from typing import Tuple

import firebase_admin
import sentry_sdk
from google.api_core import exceptions, retry
from google.api_core.retry import if_exception_type
from sentry_sdk.integrations.gcp import GcpIntegration

from phenoback.utils import glogging
from phenoback.utils.gcloud import (
    get_collection_path,
    get_document_id,
    get_field,
    get_fields_updated,
    get_project,
    get_version,
    is_create_event,
    is_delete_event,
    is_field_updated,
    is_update_event,
)


def _sentry_environment() -> Tuple[str, float]:
    project = get_project()
    if project == "phaenonet":
        return ("production", 1.0)
    elif project == "phaenonet-test":
        return ("test", 1.0)
    else:
        return ("local", 0.0)


sentry_sdk.init(
    release=get_version(),
    environment=_sentry_environment()[0],
    dsn="https://2f043e3c7dd54efa831b9d44b20cf742@o510696.ingest.sentry.io/5606957",
    integrations=[GcpIntegration()],
    traces_sample_rate=_sentry_environment()[1],
)

firebase_admin.initialize_app(
    options={"storageBucket": os.environ.get("storageBucket")}
)

log = None  # pylint: disable=invalid-name

ANALYTIC_PHENOPHASES = ("BEA", "BLA", "BFA", "BVA", "FRA")


@contextmanager  # workaround as stackdriver fails to capture stackstraces
def setup(data, context):
    try:
        global log  # pylint: disable=global-statement,invalid-name
        glogging.init(time.time())
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
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
        observation.updated_observation(individual_id, phenophase, observation_date)


@retry.Retry()
def process_observation_update_analytics(data, context):
    """
    Updates analytical values in Firestore if the observation date was modified on a observation document.
    """
    with setup(data, context):
        if is_field_updated(data, "date") or is_field_updated(data, "reprocess"):
            process_observation_create_analytics(data, context)


@retry.Retry()
def process_observation_delete_analytics(data, context):
    """
    Updates analytical values in Firestore if an observation was deleted.
    """
    with setup(data, context):
        from phenoback.functions import observation

        observation_id = get_document_id(context)
        phenophase = get_field(data, "phenophase", old_value=True)
        individual_id = (get_field(data, "individual_id", old_value=True),)
        source = get_field(data, "source", old_value=True)
        year = get_field(data, "year", old_value=True)
        species = get_field(data, "species", old_value=True)
        observation_date = get_field(data, "date", old_value=True)

        if phenophase in ANALYTIC_PHENOPHASES:
            from phenoback.functions import analytics

            log.info("Remove observation %s", observation_id)
            analytics.process_remove_observation(
                observation_id,
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
        observation.removed_observation(individual_id, observation_date)


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
def process_user_write_update_invite(data, context):
    """
    Processes invite related documents if a user is created, modified or deleted.
    """
    with setup(data, context):
        from phenoback.functions.invite import register

        user_id = get_document_id(context)
        nickname = get_field(
            data, "nickname", expected=False
        )  # don't warn on delete event

        if is_update_event(data) and is_field_updated(data, "nickname"):
            log.debug("update nickname on invites for user %s", user_id)
            register.change_nickname(user_id, nickname)
        elif is_delete_event(data):
            log.debug("delete invites for user %s", user_id)
            register.delete_user(user_id)
        elif is_create_event(data):
            log.debug("update invites for user %s", user_id)
            register.register_user(user_id)
        else:
            log.debug("Nothing to do for %s", user_id)


@retry.Retry()
def import_meteoswiss_data_publish(data, context):
    """
    Imports meteoswiss stations and observations.
    """
    with setup(data, context):
        from phenoback.functions import meteoswiss_import as meteoswiss

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
            log.info(
                "update created ts on document %s (%s)",
                context.resource,
                get_field(data, "source", expected=False),
            )
            documents.update_created_document(collection_path, document_id)
        elif is_update_event(data) and not is_field_updated(
            data, documents.MODIFIED_KEY
        ):
            log.info(
                "update modified ts on document %s %s (%s)",
                context.resource,
                get_fields_updated(data),
                get_field(data, "source", expected=False),
            )
            documents.update_modified_document(collection_path, document_id)
        elif is_delete_event(data):
            log.info("document %s was deleted", context.resource)
        else:
            log.debug(
                "Nothing to do for document %s (%s)",
                context.resource,
                get_field(data, "source", old_value=True, expected=False),
            )


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


def rollover_manual(data, context):
    """
    Rollover the phenoyear and creates data for meteoswiss export.
    Rollover is based on the year defined in the dynamic configuration
    definition in firestore.
    """
    with setup(data, context):
        from phenoback.functions import meteoswiss_export, rollover

        meteoswiss_export.process()
        rollover.rollover()


@retry.Retry()
def export_meteoswiss_data_manual(data, context):
    """
    Manually trigger a meteoswiss export for a given year.
    """
    with setup(data, context):
        from phenoback.functions import meteoswiss_export

        meteoswiss_export.process(data.get("year"))


@retry.Retry()
def process_invite_write(data, context):
    """
    Send email invites if invite is created or resend is set
    """
    with setup(data, context):
        from phenoback.functions.invite import invite

        # process if new invite or resend was changed but not deleted
        if is_create_event(data) or (
            is_field_updated(data, "resend")
            and get_field(data, "resend", expected=False)
        ):
            invite.process(
                get_document_id(context),
                get_field(data, "email"),
                get_field(data, "locale"),
                get_field(data, "user"),
                get_field(data, "sent", expected=False),
            )


@retry.Retry()
def e2e_clear_user_individuals_http(request):
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    from collections import namedtuple

    Context = namedtuple("context", "event_id")
    context = Context(event_id=time.time())

    with setup(request, context):
        from phenoback.functions import e2e

        e2e.delete_user_individuals("q7lgBm5nm7PUkof20UdZ9D4d0CV2")


def promote_ranger_http(request):
    """
    Promotes a normal user to Ranger.
    """
    from collections import namedtuple
    from http import HTTPStatus

    from flask import Response

    Context = namedtuple("context", "event_id")
    context = Context(event_id=time.time())

    content_type = request.headers["content-type"]
    if content_type == "application/json":
        request_json = request.get_json(silent=True)
        if not (request_json and "email" in request_json):
            msg = "JSON is invalid, or missing a 'email' property"
            log.warning(msg)
            return Response(msg, HTTPStatus.BAD_REQUEST)
    else:
        msg = f"Unknown content type: {content_type}, application/json required"
        return Response(msg, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    with setup(request_json, context):
        from phenoback.functions import phenorangers

        return phenorangers.promote(request_json["email"])
