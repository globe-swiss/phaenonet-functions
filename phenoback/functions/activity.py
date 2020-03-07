import phenoback
from firebase_admin import firestore
from google.cloud.firestore_v1.client import Client


_db = None


def get_client() -> Client:
    global _db
    if not _db:
        _db = firestore.client()
    return _db


def process_activity(activity_id, individual: str, user_id: str):
    users_ref = get_client().collection('users')
    following_users_query = users_ref.where('following_users', 'array_contains', user_id)
    following_individuals_query = users_ref.where('following_individuals', 'array_contains', individual)

    followers = [user.id for user in following_individuals_query.stream()]
    for user in following_users_query.stream():
        followers.append(user.id)

    print("Found %i followers for activity %s" % (len(followers), activity_id))
    if followers:
        activity_ref = get_client().collection('activities').document(activity_id)
        activity_ref.update({u'followers': followers})
