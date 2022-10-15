# pylint: disable=unused-argument
import json

import google.cloud.pubsub_v1
import pytest

from phenoback.utils import pubsub

PROJECT = "project"
TOPIC = "topic"
TOPIC_PATH = "topic_path"


@pytest.fixture
def fkn_env(mocker) -> None:
    mocker.patch("phenoback.utils.gcloud.get_project", return_value=PROJECT)


@pytest.fixture
def publisher(mocker, fkn_env) -> pubsub.Publisher:
    client_mock = mocker.patch.object(
        google.cloud.pubsub_v1, "PublisherClient", autospec=True
    )
    client_mock.topic_path.return_value = TOPIC_PATH
    mocker.patch("google.cloud.pubsub_v1.PublisherClient", return_value=client_mock)
    return pubsub.Publisher(TOPIC)


def test_init(publisher: pubsub.Publisher):
    client_mock = publisher.client

    assert publisher.topic == TOPIC
    assert publisher.topic_path == TOPIC_PATH
    assert publisher.project == PROJECT
    client_mock.topic_path.assert_called_with(PROJECT, TOPIC)


def test_send__string(publisher: pubsub.Publisher):
    client_mock = publisher.client
    payload = "foo"
    publisher.send(payload)

    client_mock.publish.assert_called_with(TOPIC_PATH, payload.encode("utf-8"))
    client_mock.publish.return_value.result.assert_called()


def test_send__dict(publisher: pubsub.Publisher):
    client_mock = publisher.client
    payload = {"foo": "bar"}
    publisher.send(payload)

    client_mock.publish.assert_called_with(
        TOPIC_PATH, json.dumps(payload).encode("utf-8")
    )
    client_mock.publish.return_value.result.assert_called()


def test_send__metadata(publisher: pubsub.Publisher):
    client_mock = publisher.client
    payload = "foo"
    metadata = {"bar": "baz"}
    publisher.send(payload, metadata)

    client_mock.publish.assert_called_with(
        TOPIC_PATH, payload.encode("utf-8"), bar="baz"
    )
    client_mock.publish.return_value.result.assert_called()
