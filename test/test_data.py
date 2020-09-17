from datetime import datetime

import pytest

from phenoback.utils import data as d, firestore as f


def test_update_get_phenoyear():
    data = {"important": "stuff is not removed"}
    f.write_document("definitions", "config_dynamic", data)
    d.update_phenoyear(2013)
    assert d.get_phenoyear() == 2013


def test_update_phenoyear__preserve_data():
    data = {"important": "stuff is not removed"}
    f.write_document("definitions", "config_dynamic", data)
    d.update_phenoyear(2013)
    result = f.get_document("definitions", "config_dynamic")
    assert result["important"] == "stuff is not removed"


@pytest.mark.parametrize(
    "individual, expected",
    [
        ({"some": "attribute", "last_observation_date": datetime.now()}, True),
        ({"some": "attribute"}, False),
    ],
)
def test_has_observation_date(individual, expected):
    assert d.has_observations(individual) == expected
