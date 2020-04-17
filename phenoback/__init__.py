import logging
import os
import firebase_admin
from firebase_admin import credentials

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

_PROJECT = 'phaenonet-test'
_TYPE = 'firebase-adminsdk'

credential_file = os.path.join(os.path.dirname(__file__), '..', 'credentials',
                               '%s-%s.json' % (_PROJECT, _TYPE))

if os.path.isfile(credential_file):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_file

    cred = credentials.Certificate(credential_file)
    firebase_admin.initialize_app(cred, {
        'storageBucket': '%s.appspot.com' % _PROJECT
    })

    log.info('app initialized with local credentials %s' % credential_file)
