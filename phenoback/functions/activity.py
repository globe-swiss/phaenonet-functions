import logging
from typing import Set

from phenoback.utils.firestore import query_collection, update_document

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def process_activity(activity_id, individual: str, user_id: str) -> bool:
    followers = get_followers(individual, user_id)

    if followers:
        log.info('Setting %i followers on activity %s' % (len(followers), activity_id))
        update_document('activities', activity_id, {u'followers': list(followers)})
        log.debug('Set followers on %s: %s' % (activity_id, str(followers)))
        return True
    else:
        log.debug('No followers on activity %s' % activity_id)
        return False


def get_followers(individual: str, user_id: str) -> Set[str]:
    following_users_query = query_collection('users', 'following_users', 'array_contains', user_id)
    following_individuals_query = query_collection('users', 'following_individuals', 'array_contains', individual)

    followers = {user.id for user in following_individuals_query.stream()}
    for user in following_users_query.stream():
        followers.add(user.id)
    return followers
