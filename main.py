# allow import outside toplevel as not all modules need to be loaded for every function
# pylint: disable=import-outside-toplevel
import base64
import json
import logging
import os
from contextlib import contextmanager
from http import HTTPStatus
from typing import Tuple, Union

import firebase_admin
import flask
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

log: logging.Logger = None  # pylint: disable=invalid-name

ANALYTIC_PHENOPHASES = ("BEA", "BLA", "BFA", "BVA", "FRA")


@contextmanager  # workaround as stackdriver fails to capture stackstraces
def setup(data: Union[dict, flask.Request], context=None, level=logging.DEBUG):
    try:
        global log  # pylint: disable=global-statement,invalid-name
        glogging.init()
        log = logging.getLogger(__name__)
        log.setLevel(level)
        if context:
            log.debug(context)
        if data:
            if isinstance(data, flask.Request):
                data = data.json if data.is_json else data.data
            log.debug(data)
        yield
    except Exception:
        log.exception("Fatal error in cloud function")
        raise


@contextmanager
def execute():
    try:
        yield
    except Exception as ex:  # pylint: disable=broad-except
        log.error("Error in execution", exc_info=ex)


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
        observation.updated_observation(individual_id)


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
        individual_id = get_field(data, "individual_id", old_value=True)
        source = get_field(data, "source", old_value=True)
        year = get_field(data, "year", old_value=True)
        species = get_field(data, "species", old_value=True)

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
        observation.updated_observation(individual_id)


@retry.Retry()
def fs_users_write(data, context):
    """
    Execute all functions to user related document changes (created, modified or deleted).
    """
    with setup(data, context):
        with execute():
            from phenoback.functions import users

            users.main(data, context)
        with execute():
            from phenoback.functions.invite import register

            register.main(data, context)


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
        source = get_field(data, "source", expected=False) or get_field(
            data, "source", old_value=True, expected=False
        )

        if is_create_event(data):
            log.debug("document %s was created (%s)", context.resource, source)
            documents.update_created_document(collection_path, document_id)
        elif is_update_event(data):
            log.debug("document %s was updated (%s)", context.resource, source)
            documents.update_modified_document(
                collection_path,
                document_id,
                get_fields_updated(data),
                get_field(data, documents.CREATED_KEY, old_value=True, expected=False),
            )
        elif is_delete_event(data):
            log.debug("document %s was deleted (%s)", context.resource, source)
        else:  # pragma: no cover
            log.error("Unexpected case for %s (%s)", context.resource, source)


@retry.Retry(predicate=if_exception_type(exceptions.NotFound))
def create_thumbnail_finalize(data, context):
    """
    Creates thumbnails for images uploaded to google cloud storage.
    """
    with setup(data, context):
        pathfile = data["name"]
        if pathfile.startswith("images/"):
            from phenoback.functions import thumbnails

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


def enqueue_individual_map_write(data, context):
    with setup(data, context):
        import phenoback.functions.map

        if not is_delete_event(data):
            phenoback.functions.map.enqueue_change(
                get_document_id(context),
                get_fields_updated(data),
                get_field(data, "species", expected=False),
                get_field(data, "station_species", expected=False),
                get_field(data, "type"),
                get_field(data, "last_phenophase", expected=False),
                get_field(data, "geopos"),
                get_field(data, "source"),
                get_field(data, "year"),
                get_field(data, "deveui", expected=False),
            )
        else:
            phenoback.functions.map.delete(
                get_field(data, "year", old_value=True), get_document_id(context)
            )


def process_individual_map_http(request: flask.Request):
    with setup(request):
        import phenoback.functions.map

        phenoback.functions.map.process_change(request.get_json(silent=True))
        return flask.Response("ok", HTTPStatus.OK)


@retry.Retry()
def e2e_clear_user_individuals_http(request: flask.Request):
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    with setup(request):
        from phenoback.functions import e2e

        e2e.delete_user_individuals("q7lgBm5nm7PUkof20UdZ9D4d0CV2")
        return flask.Response("ok", HTTPStatus.OK)


def promote_ranger_http(request: flask.Request):
    """
    Promotes a normal user to Ranger.
    """
    with setup(request):
        content_type = request.headers["content-type"]
        if content_type == "application/json":
            request_json = request.get_json(silent=True)
            if not (request_json and "email" in request_json):
                msg = "JSON is invalid, or missing a 'email' property"
                log.warning(msg)
                return flask.Response(msg, HTTPStatus.BAD_REQUEST)
        else:
            msg = f"Unknown content type: {content_type}, application/json required"
            return flask.Response(msg, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        from phenoback.functions import phenorangers

        return phenorangers.promote(request_json["email"])


def import_wld_data_finalize(data, context):
    """
    Import wld data on file upload to private/wld_import
    """
    with setup(data, context):
        pathfile = data["name"]
        if pathfile.startswith("private/wld_import/"):
            from phenoback.functions import wld_import

            log.info("Import wld data for %s", pathfile)
            wld_import.import_data(pathfile)


def process_dragino_http(request: flask.Request):
    with setup(request):
        from phenoback.functions.iot import dragino

        if request.is_json:
            dragino.process_dragino(request.json)
        else:  # pragma: no cover
            log.error("No json headers found")
            return flask.Response("No json payload", HTTPStatus.BAD_REQUEST)
        return flask.Response("ok", HTTPStatus.OK)


def process_dragino_phaenonet(event, context):
    # attributes = event["attributes"]
    data = base64.b64decode(event["data"])
    json_data = json.loads(data)
    with setup(json_data, context):
        from phenoback.functions.iot import app

        app.process_dragino(json_data)


def process_dragino_bq(event, context):
    # attributes = event["attributes"]
    data = base64.b64decode(event["data"])
    json_data = json.loads(data)
    with setup(json_data, context):
        from phenoback.utils import bq

        bq.insert_data("iot.raw", json_data)


def process_dragino_permarobotics(event, context):
    # attributes = event["attributes"]
    data = base64.b64decode(event["data"])
    json_data = json.loads(data)
    with setup(json_data, context):
        from phenoback.functions.iot import permarobotics

        permarobotics.send_permarobotics(json_data)


def set_sensor_http(request: flask.Request):
    with setup(request):
        from phenoback.functions.iot import app

        msg = "ok"
        status = HTTPStatus.OK
        individual = request.json.get("individual")
        deveui = request.json.get("deveui")
        year = request.json.get("year")

        if request.is_json and deveui and individual and year:
            if not app.set_sensor(individual, year, deveui):
                msg = f"individual {individual} not found in {year}"
                status = HTTPStatus.NOT_FOUND
                log.error(msg)
        else:
            msg = f"Invalid request (json={request.is_json}, individual={individual}, year={year}, deveui={deveui}"
            status = HTTPStatus.BAD_REQUEST
            log.error(msg)
        return flask.Response(msg, status)


def test(data, context):  # pragma: no cover
    from time import sleep

    from phenoback.utils import gcloud as g

    with setup(data, context):
        log.info("Environment: %s", str(os.environ))
        sleep(1)
        log.log(
            level=logging.ERROR if g.get_function_name() != "test" else logging.INFO,
            msg=("Function Name: %s", g.get_function_name()),
        )
        sleep(1)
        log.log(
            level=logging.ERROR if g.get_project() == "Unknown" else logging.INFO,
            msg=("Project: %s", g.get_project()),
        )
        sleep(1)
        log.log(
            level=logging.ERROR if g.get_app_host() == "Unknown" else logging.INFO,
            msg=("App Host: %s", g.get_app_host()),
        )
        sleep(1)
        log.log(
            level=logging.ERROR if g.get_version() == "Unknown" else logging.INFO,
            msg=("Version: %s", g.get_version()),
        )
        sleep(1)
        log.debug("L - debug")
        sleep(1)
        log.info("L - info")
        sleep(1)
        log.warning("L - warning")
        sleep(1)
        log.error("L - error")
        sleep(1)
        log.critical("L - critical")
        sleep(1)
        log.exception("L - exception", exc_info=Exception("myException"))
        sleep(1)

        with setup("test data", "test context"):
            raise KeyError("Should log")
