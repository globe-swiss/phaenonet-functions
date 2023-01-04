from collections import namedtuple
from typing import List

import google
import pytest

from phenoback.functions import activity

User = namedtuple("user", "id")


@pytest.mark.parametrize(
    "phenophase, is_create, date_updated, is_delete, expected",
    [
        ("XXX", True, False, False, True),
        ("XXX", False, True, False, True),
        ("XXX", False, False, True, True),
        ("XXX", False, False, False, False),
    ],
)
def test_main(
    mocker, data, context, phenophase, is_create, date_updated, is_delete, expected
):
    mock = mocker.patch("phenoback.functions.activity.process_observation")
    mocker.patch("phenoback.utils.gcloud.is_create_event", return_value=is_create)
    mocker.patch("phenoback.utils.gcloud.is_field_updated", return_value=date_updated)
    mocker.patch("phenoback.utils.gcloud.is_delete_event", return_value=is_delete)
    mocker.patch("phenoback.utils.gcloud.get_field", return_value=phenophase)

    activity.main(data, context)
    assert mock.called == expected


@pytest.mark.parametrize(
    "followers, expected",
    [({"a_follower"}, True), ({"a_follower", "another_follower"}, True), ({}, False)],
)
def test_process_observation__status(mocker, followers, expected):
    mocker.patch("phenoback.utils.data.get_individual")
    mocker.patch("phenoback.utils.data.get_phenophase")
    mocker.patch("phenoback.utils.data.get_species")
    mocker.patch("phenoback.utils.data.get_user")
    mocker.patch("phenoback.functions.activity.get_followers", return_value=followers)
    update_mock = mocker.patch("phenoback.utils.firestore.write_document")

    assert expected == activity.process_observation(
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
    )
    assert update_mock.called == expected


def test_process_observation__values(mocker):
    followers = {"a_follower", "another_follower"}
    mocker.patch("phenoback.utils.data.get_individual")
    mocker.patch("phenoback.utils.data.get_phenophase")
    mocker.patch("phenoback.utils.data.get_species")
    mocker.patch("phenoback.utils.data.get_user")
    mocker.patch("phenoback.functions.activity.get_followers", return_value=followers)
    update_mock = mocker.patch("phenoback.utils.firestore.write_document")

    activity.process_observation(
        "event_id",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
    )
    assert update_mock.call_args[0][0] == "activities"
    assert update_mock.call_args[0][1] == "event_id"
    assert update_mock.call_args[0][2]["followers"] == list(followers)


def test_process_observation__no_individual_found(mocker):
    mocker.patch("phenoback.utils.data.get_individual", return_value=None)
    activity.log = mocker.Mock()

    activity.process_observation(
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
        "ignored",
    )

    activity.log.error.assert_called()


@pytest.mark.parametrize(
    "user_following, individuals_following",
    [
        (["user1"], []),
        ([], ["user1"]),
        (["user1"], ["user2"]),
        (["user1", "user2"], ["user3", "user4"]),
        (["user1"], ["user1"]),
        ([], []),
    ],
)
def test_get_followers(mocker, user_following, individuals_following):
    expected = set(user_following).union(individuals_following)

    # mock
    users_following_mock = mocker.patch.object(google.cloud.firestore_v1.query, "Query")
    users_following_mock.stream.return_value = _user_str_to_namedtupel(user_following)
    individuals_following_mock = mocker.patch.object(
        google.cloud.firestore_v1.query, "Query"
    )
    individuals_following_mock.stream.return_value = _user_str_to_namedtupel(
        individuals_following
    )
    mocker.patch(
        "phenoback.utils.firestore.query_collection",
        side_effect=[users_following_mock, individuals_following_mock],
    )

    assert expected == activity.get_followers("ignored", "ignored")


def _user_str_to_namedtupel(users: List[str]):
    return [User(id=user) for user in users]
