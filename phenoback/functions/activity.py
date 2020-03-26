from phenoback.gcloud.utils import firestore_client


def process_activity(activity_id, individual: str, user_id: str):
    users_ref = firestore_client().collection('users')
    following_users_query = users_ref.where('following_users', 'array_contains', user_id)
    following_individuals_query = users_ref.where('following_individuals', 'array_contains', individual)

    followers = [user.id for user in following_individuals_query.stream()]
    for user in following_users_query.stream():
        followers.append(user.id)

    print("Found %i followers for activity %s" % (len(followers), activity_id))
    if followers:
        activity_ref = firestore_client().collection('activities').document(activity_id)
        activity_ref.update({u'followers': followers})
