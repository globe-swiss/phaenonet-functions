from flask import Response

from phenoback.functions import e2e
from phenoback.utils import data as d
from phenoback.utils import firestore as f


def test_main(mocker):
    e2e_mock = mocker.patch("phenoback.functions.e2e.delete_user_individuals")
    assert isinstance(e2e.main("ignored"), Response)
    e2e_mock.assert_called_once()
    e2e_mock.assert_called_with("q7lgBm5nm7PUkof20UdZ9D4d0CV2")


def test_delete_all_individuals():
    d.write_individual("u1_i1", {"user": "u1"})
    d.write_individual("u1_i2", {"user": "u1"})
    d.write_individual("u2_i1", {"user": "u2"})
    d.write_individual("u2_i1", {"user": "u2"})

    e2e.delete_user_individuals("u1")
    for individual in d.query_individuals("user", "==", "u1").stream():
        assert False, individual
    for individual in f.get_collection("individuals").stream():
        assert individual.to_dict()["user"] == "u2"
