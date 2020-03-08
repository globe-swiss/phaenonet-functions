import os
import firebase_admin
from firebase_admin import credentials

credential_file = os.path.join(os.path.dirname(__file__), '..', 'phaenonet-firebase-adminsdk-feq3i-040e674576.json')

if os.path.isfile(credential_file):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_file

    print(credential_file)

    # Use a service account
    cred = credentials.Certificate(credential_file)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'phaenonet.appspot.com'
    })

    print('app initialized')
else:
    print('INFO: no credential file found. App initialization skipped.')
