from flask import Response

from phenoback.functions import e2e
from phenoback.utils import data as d
from phenoback.utils import firestore as f


def test_main(mocker):
    e2e_mock = mocker.patch("phenoback.functions.e2e.delete_user_individuals")
    assert isinstance(e2e.main("ignored"), Response)
    e2e_mock.assert_called_once()
    e2e_mock.assert_called_with(
        ["q7lgBm5nm7PUkof20UdZ9D4d0CV2", "JIcn8kFpI4fYYcbdi9QzPlrHomn1"]
    )


def test_delete_all_individuals():
    d.write_individual("u1_i1", {"user": "u1"})
    d.write_individual("u1_i2", {"user": "u1"})
    d.write_individual("u2_i1", {"user": "u2"})
    d.write_individual("u2_i2", {"user": "u2"})
    d.write_individual("u3_i1", {"user": "u3"})
    d.write_individual("u3_i2", {"user": "u3"})

    e2e.delete_user_individuals(["u1", "u3"])
    for individual in f.get_collection("individuals").stream():
        assert individual.to_dict()["user"] == "u2"
