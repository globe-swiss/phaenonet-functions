# allow import outside toplevel as not all modules need to be loaded for every function
# pylint: disable=import-outside-toplevel
import logging
import os
from contextlib import contextmanager

import firebase_admin
import sentry_sdk
from flask import Request
from google.api_core import exceptions, retry
from google.api_core.retry import if_exception_type
from sentry_sdk.integrations.gcp import GcpIntegration

import phenoback.utils.gcloud as g
from phenoback.utils import glogging


def sentry_environment() -> tuple[str, float]:
    project = g.get_project()
    if project == "phaenonet":
        return ("production", 1.0, 0.0)
    elif project == "phaenonet-test":
        return ("test", 1.0, 0.0)
    else:
        return ("local", 0.0, 0.0)


sentry_sdk.init(
    release=g.get_version(),
    environment=sentry_environment()[0],
    dsn="https://2f043e3c7dd54efa831b9d44b20cf742@o510696.ingest.sentry.io/5606957",
    integrations=[GcpIntegration()],
    sample_rate=sentry_environment()[1],
    traces_sample_rate=sentry_environment()[2],
)

firebase_admin.initialize_app(
    options={"storageBucket": os.environ.get("storageBucket")}
)

log: logging.Logger = None  # pylint: disable=invalid-name


@contextmanager  # workaround as stackdriver fails to capture stackstraces
def setup(data: dict | Request | None, context=None, level=logging.DEBUG):
    """
    Setup logging and and capture exceptions.
    :param data: May be a dict, a http request or None.
    """
    try:
        global log  # pylint: disable=global-statement,invalid-name
        glogging.init()
        log = logging.getLogger(__name__)
        log.setLevel(level)
        if context:
            log.debug(context)
        if data:
            if isinstance(data, Request):
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


@retry.Retry()
def fs_observations_write(data, context):
    with setup(data, context):
        with invoke():
            from phenoback.functions import activity

            activity.main(data, context)
        with invoke():
            from phenoback.functions import analytics

            analytics.main_enqueue(data, context)
        with invoke():
            from phenoback.functions import individual

            individual.main(data, context)


@retry.Retry()
def http_observations_write__analytics(request: Request):
    with setup(request):
        with invoke():
            from phenoback.functions import analytics

            return analytics.main_process(request)


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
    data = g.get_data(event)
    with setup(data, context):
        with invoke():
            from phenoback.functions import meteoswiss_import

            meteoswiss_import.main(data, context)


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
    data = g.get_data(event)
    with setup(data, context):
        with invoke():
            from phenoback.functions import meteoswiss_export, rollover

            meteoswiss_export.main(data, context)
            rollover.main(data, context)


@retry.Retry()
def ps_export_meteoswiss_data(event, context):
    """
    Manually trigger a meteoswiss export for a given year.
    """
    data = g.get_data(event)
    with setup(data, context):
        with invoke():
            from phenoback.functions import meteoswiss_export

            meteoswiss_export.main(data, context)


@retry.Retry()
def fs_invites_write(data, context):
    with setup(data, context):
        with invoke():
            from phenoback.functions.invite import invite

            invite.main(data, context)


@retry.Retry()
def fs_individuals_write(data, context):
    with setup(data, context):
        with invoke():
            import phenoback.functions.map

            phenoback.functions.map.main_enqueue(data, context)
        with invoke():
            import phenoback.functions.iot.app

            phenoback.functions.iot.app.main_individual_updated(data, context)


def http_individuals_write__map(request: Request):
    with setup(request):
        with invoke():
            import phenoback.functions.map

            return phenoback.functions.map.main_process(request)


@retry.Retry()
def http_reset_e2e_data(request: Request):
    with setup(request):
        with invoke():
            from phenoback.functions import e2e

            return e2e.main_reset(request)


@retry.Retry()
def http_restore_e2e_users(request: Request):
    with setup(request):
        with invoke():
            from phenoback.functions import e2e

            return e2e.main_restore(request)


def http_promote_ranger(request: Request):
    """
    Promotes a normal user to Ranger.
    """
    with setup(request):
        with invoke():
            from phenoback.functions import phenorangers

            return phenorangers.main(request)


def http_iot_dragino(request: Request):
    with setup(request):
        with invoke():
            from phenoback.functions.iot import dragino

            return dragino.main(request)


def ps_iot_dragino(event, context):
    data = g.get_data(event)
    with setup(data, context):
        with invoke():
            from phenoback.functions.iot import app

            app.main(data, context)
        with invoke():
            from phenoback.functions.iot import permarobotics

            # only sent data from production environment to permarobotics
            if g.get_project() == "phaenonet":
                permarobotics.main(data, context)
        with invoke():
            from phenoback.functions.iot import bq

            bq.main(data, context)


def ps_process_statistics(event, context):
    data = g.get_data(event)
    with setup(data, context):
        with invoke():
            from phenoback.functions.statistics import weekly

            return weekly.main(data, context)


def test(data, context):  # pragma: no cover
    from time import sleep

    with setup(data, context):
        log.info("Environment: %s", str(os.environ))
        sleep(1)
        log.log(
            logging.ERROR if g.get_function_name() != "test" else logging.INFO,
            "Function Name: %s",
            g.get_function_name(),
        )
        sleep(1)
        log.log(
            logging.ERROR if g.get_project() != "phaenonet-test" else logging.INFO,
            "Project: %s",
            g.get_project(),
        )
        sleep(1)
        log.log(
            (
                logging.ERROR
                if g.get_app_host() != "phaenonet-test.web.app"
                else logging.INFO
            ),
            "App Host: %s",
            g.get_app_host(),
        )
        sleep(1)
        log.log(
            logging.ERROR if not g.get_version().startswith("test@") else logging.INFO,
            "Version: %s",
            g.get_version(),
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

        with setup(
            "test data: with setup/invoke: should log Key Error", "test context"
        ):
            with invoke():
                raise KeyError("Should log - setup/invoke first")
            with invoke():
                raise KeyError("Should log - setup/invoke second")

        with setup("test data: with setup: should log Key Error", "test context"):
            raise KeyError("Should log - setup")
