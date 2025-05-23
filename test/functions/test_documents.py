from datetime import datetime, timezone
from unittest.mock import ANY

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
            "created": datetime.now(timezone.utc),
            "modified": datetime.now(timezone.utc),
            "data": "some data",
        },
    )
    return ("collection", "doc_id")


@pytest.mark.parametrize(
    "called, data",
    [
        (
            "updated",
            {
                "updateMask": {"fieldPaths": ["modified"]},
                "oldValue": {
                    "fields": {
                        "modified": {"timestampValue": str(datetime.now(timezone.utc))}
                    }
                },
                "value": {
                    "fields": {
                        "modified": {"timestampValue": str(datetime.now(timezone.utc))}
                    }
                },
            },
        ),
        (
            "created",
            {
                "updateMask": {},
                "oldValue": {},
                "value": {
                    "fields": {
                        "modified": {"timestampValue": str(datetime.now(timezone.utc))}
                    }
                },
            },
        ),
        (
            "deleted",
            {
                "updateMask": {"fieldPaths": ["modified"]},
                "oldValue": {
                    "fields": {
                        "modified": {"timestampValue": str(datetime.now(timezone.utc))}
                    }
                },
                "value": {},
            },
        ),
    ],
)
def test_main(mocker, called, data):
    update_modified_document_mock = mocker.patch(
        "phenoback.functions.documents.update_modified_document"
    )
    update_created_document_mock = mocker.patch(
        "phenoback.functions.documents.update_created_document"
    )
    documents.main(data, mocker.MagicMock())
    assert update_modified_document_mock.called == (called == "updated")
    assert update_created_document_mock.called == (called == "created")
    # nothing to do for delete


def test_main__overwrite_created(mocker):
    create_ts = datetime.now(timezone.utc)
    data = {
        "updateMask": {"fieldPaths": ["created", "somevalue"]},
        "oldValue": {"fields": {"created": {"timestampValue": str(create_ts)}}},
        "value": {"fields": {"somevalue": {"something"}}},
    }
    update_modified_document_mock = mocker.patch(
        "phenoback.functions.documents.update_modified_document"
    )

    documents.main(data, mocker.MagicMock())
    update_modified_document_mock.assert_called_once_with(
        ANY, ANY, data["updateMask"]["fieldPaths"], create_ts
    )


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
    created_ts = datetime.now(timezone.utc)
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
        ["sensor.value", "any_other_data"],
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
