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

import phenoback.utils.gcloud as g
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
def invoke():
    try:
        yield
    except Exception as ex:  # pylint: disable=broad-except
        log.error("Error in execution", exc_info=ex)


def fs_observations_write(data, context):
    with setup(data, context):
        with invoke():
            from phenoback.functions import activity

            activity.main(data, context)


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
        with invoke():
            from phenoback.functions import users

            users.main(data, context)
        with invoke():
            from phenoback.functions.invite import register

            register.main(data, context)


@retry.Retry()
def ps_import_meteoswiss_data(event, context):
    """
    Imports meteoswiss stations and observations.
    """
    with setup(event, context):
        with invoke():
            from phenoback.functions import meteoswiss_import

            meteoswiss_import.main(event, context)


@retry.Retry()
def fs_document_write(data, context):
    with setup(data, context):
        with invoke():
            from phenoback.functions import documents

            documents.main(data, context)


@retry.Retry(predicate=if_exception_type(exceptions.NotFound))
def st_appspot_finalize(data, context):
    with setup(data, context):
        with invoke():
            from phenoback.functions import thumbnails

            thumbnails.main(data, context)
        with invoke():
            from phenoback.functions import wld_import

            wld_import.main(data, context)


def ps_rollover_phenoyear(event, context):
    """
    Rollover the phenoyear and creates data for meteoswiss export.
    Rollover is based on the year defined in the dynamic configuration
    definition in firestore.
    """
    with setup(event, context):
        with invoke():
            from phenoback.functions import meteoswiss_export, rollover

            meteoswiss_export.main(event, context)
            rollover.main(event, context)


@retry.Retry()
def ps_export_meteoswiss_data(event, context):
    """
    Manually trigger a meteoswiss export for a given year.
    """
    with setup(event, context):
        with invoke():
            from phenoback.functions import meteoswiss_export

            meteoswiss_export.main(event, context)


@retry.Retry()
def fs_invites_write(data, context):
    with setup(data, context):
        with invoke():
            from phenoback.functions.invite import invite

            invite.main(data, context)


def fs_individuals_write(data, context):
    with setup(data, context):
        with invoke():
            import phenoback.functions.map

            phenoback.functions.map.main_enqueue(data, context)


def http_individuals_write(request: flask.Request):
    with setup(request):
        with invoke():
            import phenoback.functions.map

            return phenoback.functions.map.main_process(request)


@retry.Retry()
def http_reset_e2e_data(request: flask.Request):
    with setup(request):
        with invoke():
            from phenoback.functions import e2e

            return e2e.main(request)


def http_promote_ranger(request: flask.Request):
    """
    Promotes a normal user to Ranger.
    """
    with setup(request):
        with invoke():
            from phenoback.functions import phenorangers

            return phenorangers.main(request)


def http_iot_dragino(request: flask.Request):
    with setup(request):
        with invoke():
            from phenoback.functions.iot import dragino

            return dragino.main(request)


def ps_iot_dragino_app(event, context):
    with setup(g.get_data(event), context):
        with invoke():
            from phenoback.functions.iot import app

            app.main(event, context)


def ps_iot_dragino_bq(event, context):
    with setup(g.get_data(event), context):
        with invoke():
            from phenoback.functions.iot import bq

            bq.main(event, context)


def ps_iot_dragino_permarobotics(event, context):
    with setup(g.get_data(event), context):
        with invoke():
            from phenoback.functions.iot import permarobotics

            permarobotics.main(event, context)


def http_set_sensor(request: flask.Request):
    with setup(request):
        with invoke():
            from phenoback.functions.iot import app

            return app.main_set_sensor(request)


def test(data, context):  # pragma: no cover
    from time import sleep

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
