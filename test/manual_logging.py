import logging

import phenoback

phenoback.set_credential_env()

import main  # pylint: disable=wrong-import-position, unused-import

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

log.debug("L - debug")
log.info("L - info")
log.warning("L - warning")
log.error("L - error")
log.critical("L - critical")
log.exception("L - exception", exc_info=Exception("myException"))
