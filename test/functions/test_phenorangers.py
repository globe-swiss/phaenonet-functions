from test.util import Doc, get_random_string
from typing import List

import pytest
from flask import Request
from werkzeug.test import EnvironBuilder

from phenoback.functions import phenorangers
from phenoback.utils import data as d
from phenoback.utils import firestore as f


@pytest.fixture()
def public_user() -> Doc:
    doc_id = get_random_string(12)
    user = {"nickname": "nickname"}
    f.write_document("public_users", doc_id, user)
    return Doc(doc_id, user)


def insert_individuals(user: str, source: str, year: int, num: int = 1) -> List[str]:
    doc_ids = []
    for _ in range(num):
        doc_id = get_random_string(12)
        f.write_document(
            "individuals",
            doc_id,
            {"source": source, "user": user, "year": year},
        )
        doc_ids.append(doc_id)
    return doc_ids


def test_main(mocker):
    email = "test@example.com"
    promote_mock = mocker.patch("phenoback.functions.phenorangers.promote")
    request = Request(
        EnvironBuilder(
            method="POST",
            json={"email": email},
        ).get_environ()
    )
    phenorangers.main(request)
    promote_mock.assert_called_with(email)


def test_main__content_type():
    request = Request(
        EnvironBuilder(
            method="POST", headers={"content-type": "something"}
        ).get_environ()
    )
    assert phenorangers.main(request).status_code == 415


def test_main__email_missing():
    request = Request(
        EnvironBuilder(
            method="POST",
            json={"something": "something"},
        ).get_environ()
    )
    assert phenorangers.main(request).status_code == 400


def test_set_ranger__new_role(public_user):
    phenorangers.set_ranger(public_user.doc_id, None)
    new_user = f.get_document("public_users", public_user.doc_id)
    assert new_user.items() >= public_user.data.items()
    assert "ranger" in new_user.get("roles")


def test_set_ranger__add_role(public_user):
    existing_role = "existing_role"
    f.update_document("public_users", public_user.doc_id, {"roles": [existing_role]})

    phenorangers.set_ranger(public_user.doc_id, None)
    new_user = f.get_document("public_users", public_user.doc_id)
    assert new_user.items() >= public_user.data.items()
    assert "ranger" in new_user.get("roles")
    assert existing_role in new_user.get("roles")


def test_update_individuals__other_years(public_user):
    insert_individuals(public_user.doc_id, "old_source", 1999)
    assert phenorangers.update_individuals(public_user.doc_id, 2000, None) == 0


def test_update_individuals__other_users(public_user):
    insert_individuals("another_user", "old_source", 2000)
    assert phenorangers.update_individuals(public_user.doc_id, 2000, None) == 0


def test_update_individuals__update(public_user):
    doc_ids = insert_individuals(public_user.doc_id, "old_source", 2000)
    assert phenorangers.update_individuals(public_user.doc_id, 2000, None) == 1
    individual = d.get_individual(doc_ids[0])
    assert individual.pop("source") == "ranger"


def test_update_individuals(public_user):
    num_individuals = 3
    current_year = 2000
    old_source = "old_source"

    insert_individuals(public_user.doc_id, old_source, current_year, num_individuals)

    assert (
        phenorangers.update_individuals(public_user.doc_id, current_year, None)
        == num_individuals
    )

    cnt = 0
    for doc in (
        d.query_individuals("user", "==", public_user.doc_id)
        .where(filter=f.FieldFilter("year", "==", current_year))
        .stream()
    ):
        assert doc.to_dict().get("source") == "ranger"
        cnt += 1
    assert cnt == num_individuals


def test_get_observation_present(public_user):
    d.write_observation("some_id", {"user": public_user.doc_id, "year": 2000})
    assert phenorangers.get_observation(public_user.doc_id, 2000) == "some_id"


def test_get_observation_absent(public_user):
    assert phenorangers.get_observation(public_user.doc_id, 2000) is None


def test_promote__email_not_found(mocker, public_user):
    d.write_observation("some_id", {"user": public_user.doc_id, "year": 2000})
    mocker.patch(
        "phenoback.utils.data.user_exists",
        return_value=False,
    )
    set_ranger_spy = mocker.spy(phenorangers, "set_ranger")
    assert phenorangers.promote("some_email").status_code == 404
    set_ranger_spy.assert_not_called()


def test_promote__observations_found(mocker, public_user):
    d.write_observation("some_id", {"user": public_user.doc_id, "year": 2000})
    mocker.patch(
        "phenoback.utils.data.user_exists",
        return_value=True,
    )
    mocker.patch(
        "phenoback.utils.data.get_user_id_by_email",
        return_value=public_user.doc_id,
    )
    mocker.patch(
        "phenoback.utils.data.get_phenoyear",
        return_value=2000,
    )
    set_ranger_spy = mocker.spy(phenorangers, "set_ranger")
    assert phenorangers.promote("some_email").status_code == 409
    set_ranger_spy.assert_not_called()


def check_promote_updated(mocker, user_id, year, num):
    mocker.patch(
        "phenoback.utils.data.user_exists",
        return_value=True,
    )
    mocker.patch(
        "phenoback.utils.data.get_user_id_by_email",
        return_value=user_id,
    )
    mocker.patch(
        "phenoback.utils.data.get_phenoyear",
        return_value=year,
    )
    set_ranger_spy = mocker.spy(phenorangers, "set_ranger")
    update_individuals_spy = mocker.spy(phenorangers, "update_individuals")
    assert phenorangers.promote("some_email").status_code == 200
    set_ranger_spy.assert_called()
    update_individuals_spy.assert_called_once()
    assert update_individuals_spy.spy_return == num


def test_promote__individuals(mocker, public_user):
    year = 2000
    insert_individuals(public_user.doc_id, "old_source", year)
    check_promote_updated(mocker, public_user.doc_id, year, 1)


def test_promote__no_individuals(mocker, public_user):
    check_promote_updated(mocker, public_user.doc_id, 2000, 0)
