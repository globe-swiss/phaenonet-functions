from typing import List
from unittest.mock import call
import google.cloud.firestore_v1.collection
from collections import namedtuple, OrderedDict
import pytest
from phenoback.functions import activity

User = namedtuple('user', 'id')


@pytest.mark.parametrize('followers, expected',
                         [({'a_follower'}, True),
                          ({'a_follower', 'another_follower'}, True),
                          ({}, False)
                          ])
def test_process_activity_status(mocker, followers, expected):
    mocker.patch('phenoback.functions.activity.get_followers', return_value=followers)
    update_mock = mocker.patch('phenoback.functions.activity.update_document')

    assert expected == activity.process_activity('ignored', 'ignored', 'ignored')
    if not expected:
        update_mock.assert_not_called()


def test_process_activity_update_values(mocker):
    mocker.patch('phenoback.functions.activity.get_followers',
                 return_value=['a_follower', 'another_follower'])
    update_mock = mocker.patch('phenoback.functions.activity.update_document')

    activity.process_activity('activity_id', 'ignored', 'ignored')
    assert update_mock.call_args == call('activities', 'activity_id', {'followers': ['a_follower', 'another_follower']})


@pytest.mark.parametrize('user_following, individuals_following',
                         [(['user1'], []),
                          ([], ['user1']),
                          (['user1'], ['user2']),
                          (['user1', 'user2'], ['user3', 'user4']),
                          (['user1'], ['user1']),
                          ([], [])
                          ])
def test_process_activity(mocker, user_following, individuals_following):
    expected = set(user_following).union(individuals_following)

    # mock
    users_following_mock = mocker.patch.object(google.cloud.firestore_v1.query, 'Query')
    users_following_mock.stream.return_value = _user_str_to_namedtupel(user_following)
    individuals_following_mock = mocker.patch.object(google.cloud.firestore_v1.query, 'Query')
    individuals_following_mock.stream.return_value = _user_str_to_namedtupel(individuals_following)
    mocker.patch('phenoback.functions.activity.query_collection', side_effect=[users_following_mock,
                                                                               individuals_following_mock])
    update_mock = mocker.patch('phenoback.functions.activity.update_document')

    assert expected == activity.get_followers('ignored', 'ignored')


def _user_str_to_namedtupel(users: List[str]):
    return [User(id=user) for user in users]