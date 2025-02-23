from test.util import get_random_string

import google.api_core.exceptions
import pytest
from google.cloud.firestore_v1._helpers import ReadAfterWriteError

from phenoback.utils import firestore as f


@pytest.fixture()
def doc_id() -> str:
    return get_random_string(12)


@pytest.fixture()
def doc_id2() -> str:
    return get_random_string(13)


@pytest.fixture()
def doc() -> dict[str, str]:
    return {get_random_string(5): get_random_string(5)}


@pytest.fixture()
def doc2() -> dict[str, str]:
    return {get_random_string(6): get_random_string(6)}


@pytest.fixture()
def collection() -> str:
    return get_random_string(5)


def test_get_write_document(collection, doc_id, doc):
    f.write_document(collection, doc_id, doc)
    assert f.get_document(collection, doc_id) == doc


def test_write_document__overwrite(collection, doc_id, doc, doc2):
    assert doc != doc2
    f.write_document(collection, doc_id, doc)
    f.write_document(collection, doc_id, doc2)

    assert f.get_document(collection, doc_id) == doc2


def test_write_document__merge(collection, doc_id, doc, doc2):
    assert doc != doc2
    f.write_document(collection, doc_id, doc)
    f.write_document(collection, doc_id, doc2, merge=True)

    result = f.get_document(collection, doc_id)
    assert result != doc
    assert result != doc2
    doc.update(doc2)
    assert result == doc


def test_delete_document(collection, doc_id, doc):
    f.write_document(collection, doc_id, doc)
    assert f.get_document(collection, doc_id)
    f.delete_document(collection, doc_id)
    assert not f.get_document(collection, doc_id)


def test_update_document(collection, doc_id, doc, doc2):
    assert doc != doc2
    f.write_document(collection, doc_id, doc)
    f.update_document(collection, doc_id, doc2)

    result = f.get_document(collection, doc_id)
    assert result != doc
    assert result != doc2
    doc.update(doc2)
    assert result == doc


def test_update_document__non_existing(collection, doc_id, doc, doc2):
    assert doc != doc2
    try:
        f.update_document(collection, doc_id, doc2)
    except google.api_core.exceptions.NotFound:
        pass  # expected


def test_get_collection(collection, doc_id, doc_id2, doc, doc2):
    assert doc != doc2
    f.write_document(collection, doc_id, doc)
    f.write_document(collection, doc_id2, doc2)
    assert len(list(f.get_collection(collection).stream())) == 2


def test_get_collection__empty(collection):
    assert len(list(f.get_collection(collection).stream())) == 0


def test_collection(collection, doc_id, doc_id2, doc):
    doc2 = {"key": "value"}
    assert doc != doc2
    f.write_document(collection, doc_id, doc)
    f.write_document(collection, doc_id2, doc2)
    result = list(f.collection(collection).stream())
    assert len(result) == 2
    assert all(x in (result[0].to_dict(), result[1].to_dict()) for x in [doc, doc2])


def test_query_collection(collection, doc_id, doc_id2, doc):
    doc2 = {"key": "value"}
    assert doc != doc2
    f.write_document(collection, doc_id, doc)
    f.write_document(collection, doc_id2, doc2)
    result = list(f.query_collection(collection, "key", "==", "value").stream())
    assert len(result) == 1
    assert result[0].to_dict() == doc2


def test_query_collection__no_result(collection, doc_id, doc_id2, doc):
    f.write_document(collection, doc_id, doc)
    f.write_document(collection, doc_id2, {"key": "value"})
    result = list(f.query_collection(collection, "key", "==", "miss").stream())
    assert len(result) == 0


def test_write_batch(collection):
    size = 32
    batch = []
    for i in range(size):
        batch.append({"id": i, "value": i})

    assert f.write_batch(collection, "id", batch, commit_size=5) == 0
    assert len(list(f.get_collection(collection).stream())) == size


def test_write_batch__transaction(collection):
    @f.transactional
    def write_batch_transaction(transaction, collection, batch):
        f.get_document(collection, "non_existing_id", transaction=transaction)
        assert f.write_batch(collection, "id", batch, transaction=transaction) == size

    size = 32
    batch = []
    for i in range(size):
        batch.append({"id": i, "value": i})

    write_batch_transaction(f.get_transaction(), collection, batch)

    assert len(list(f.get_collection(collection).stream())) == size


def test_delete_collection(collection):
    size = 30
    batch = []
    for i in range(size):
        batch.append({"id": i, "value": i})
    f.write_batch(collection, "id", batch)

    f.delete_collection(collection, 5)

    assert len(list(f.get_collection(collection).stream())) == 0


def test_delete_batch(collection):
    properties = 3
    properties_size = 10

    batch = []
    for prop in range(properties):
        for prop_size in range(properties_size):
            batch.append({"id": (prop * properties_size + prop_size), "property": prop})
    f.write_batch(collection, "id", batch)

    assert (
        len(list(f.get_collection(collection).stream())) == properties * properties_size
    )

    f.delete_batch(collection, "property", "==", 2, batch_size=3)

    results = list(f.get_collection(collection).stream())
    assert len(results) == (properties - 1) * properties_size, f.docs2str(results)
    for result in results:
        assert result.to_dict().get("property") is not None
        assert result.to_dict()["property"] != 2


def test_write_document__transaction(collection, doc_id, doc):
    @f.transactional
    def write_transactional(
        transaction,
        collection,
        doc_id,
    ):
        f.write_document(collection, doc_id, doc, transaction=transaction)

    write_transactional(f.get_transaction(), collection, doc_id)
    assert f.get_document(collection, doc_id) == doc


def test_update_document__transaction(collection, doc_id, doc, doc2):
    @f.transactional
    def update_transactional(
        transaction,
        collection,
        doc_id,
    ):
        f.update_document(collection, doc_id, doc2, transaction=transaction)

    f.write_document(collection, doc_id, doc)
    update_transactional(f.get_transaction(), collection, doc_id)
    updated_doc = f.get_document(collection, doc_id)
    assert doc.items() < updated_doc.items()
    assert doc2.items() < updated_doc.items()


def test_delete_document__transaction(collection, doc_id, doc):
    @f.transactional
    def delete_transactional(
        transaction,
        collection,
        doc_id,
    ):
        f.delete_document(collection, doc_id, transaction=transaction)

    f.write_document(collection, doc_id, doc)
    delete_transactional(f.get_transaction(), collection, doc_id)

    assert f.get_document(collection, doc_id) is None


def test_get_document__transaction(collection, doc_id, doc):
    @f.transactional
    def get_transactional(
        transaction,
        collection,
        doc_id,
    ):
        return f.get_document(collection, doc_id, transaction=transaction)

    f.write_document(collection, doc_id, doc)
    assert get_transactional(f.get_transaction(), collection, doc_id) == doc


def test_get_document__transaction_fail(collection, doc_id, doc):
    @f.transactional
    def transactional__fail(transaction, collection, doc_id):
        f.write_document(collection, doc_id, doc, transaction=transaction)
        f.get_document(collection, doc_id, transaction=transaction)

    try:
        transactional__fail(f.get_transaction(), collection, doc_id)
    except ReadAfterWriteError:
        pass  # expected


def test_get_collection_documents(collection):
    docs = [{"value": "1"}, {"value": "2"}]
    f.write_document(collection, "0", docs[0])
    f.write_document(collection, "1", docs[1])

    result = f.get_collection_documents(collection)
    assert len(result) == 2
    assert docs[0] in result
    assert docs[1] in result


def test_get_count(collection, doc_id, doc):
    f.write_document(collection, doc_id, doc)
    assert f.get_count(f.get_collection(collection)) == 1
