import os
import firebase_admin
from firebase_admin import credentials

credential_file = os.path.join(os.path.dirname(__file__), '..', 'credentials',
                               'phaenonet-test-firebase-adminsdk-f8f66db4aeaa.json')

if os.path.isfile(credential_file):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_file

    cred = credentials.Certificate(credential_file)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'phaenonet-test.appspot.com'
    })

    print('INFO: app initialized with local credentials %s' % credential_file)
