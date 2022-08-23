from datetime import datetime, timezone

import pytest

from phenoback.functions import documents
from phenoback.utils import firestore as f


@pytest.fixture
def doc_nots():
    f.write_document("collection", "doc_id", {"data": "some data"})
    return ("collection", "doc_id")


@pytest.fixture
def doc_ts():
    f.write_document(
        "collection",
        "doc_id",
        {
            "created": datetime.utcnow(),
            "modified": datetime.utcnow(),
            "data": "some data",
        },
    )
    return ("collection", "doc_id")


def test_update_created_document(doc_nots):
    documents.update_created_document(*doc_nots)
    updated_doc = f.get_document(*doc_nots)
    assert isinstance(updated_doc[documents.CREATED_KEY], datetime)
    assert isinstance(updated_doc[documents.MODIFIED_KEY], datetime)
    assert updated_doc["data"]


@pytest.mark.parametrize(
    "updated_fields",
    [
        [documents.MODIFIED_KEY, documents.CREATED_KEY, "some_data"],
        [documents.MODIFIED_KEY, "some_data"],
        [documents.CREATED_KEY, "some_data"],
        ["some_data"],
    ],
)
def test_update_modified_document(doc_ts, updated_fields):
    initial_ts = f.get_document(*doc_ts)[documents.MODIFIED_KEY]
    documents.update_modified_document(*doc_ts, updated_fields)
    updated_doc = f.get_document(*doc_ts)
    assert updated_doc[documents.MODIFIED_KEY] > initial_ts
    assert updated_doc["data"]


@pytest.mark.parametrize(
    "updated_fields",
    [
        [documents.MODIFIED_KEY, documents.CREATED_KEY, "some_data"],
        [documents.MODIFIED_KEY, "some_data"],
        [documents.CREATED_KEY, "some_data"],
        ["some_data"],
    ],
)
def test_update_modified_document__create_ts(doc_ts, updated_fields):
    initial_ts = f.get_document(*doc_ts)[documents.MODIFIED_KEY]
    created_ts = datetime.utcnow().replace(tzinfo=timezone.utc)
    documents.update_modified_document(*doc_ts, updated_fields, created_ts)
    updated_doc = f.get_document(*doc_ts)
    assert updated_doc[documents.CREATED_KEY] == created_ts
    assert updated_doc[documents.MODIFIED_KEY] > initial_ts
    assert updated_doc["data"]


@pytest.mark.parametrize(
    "updated_fields",
    [
        [documents.MODIFIED_KEY],
        [documents.CREATED_KEY],
        [documents.MODIFIED_KEY, documents.CREATED_KEY],
    ],
)
def test_update_modified_document__skip_update(mocker, doc_ts, updated_fields):
    write_mock = mocker.patch("phenoback.utils.firestore.write_document")
    update_mock = mocker.patch("phenoback.utils.firestore.update_document")
    initial_ts = f.get_document(*doc_ts)[documents.MODIFIED_KEY]
    documents.update_modified_document(*doc_ts, updated_fields)
    updated_doc = f.get_document(*doc_ts)
    write_mock.assert_not_called()
    update_mock.assert_not_called()
    assert updated_doc[documents.MODIFIED_KEY] == initial_ts
    assert updated_doc["data"]
