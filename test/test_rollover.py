# pylint: disable=unused-argument
import pytest

from phenoback.functions import rollover
from phenoback.utils import data as d


@pytest.fixture()
def setup() -> None:
    """
    Setup based on rollover 2012 -> 2013.
    """
    d.write_individual(
        "2011_1",
        {
            "individual": "1",
            "source": "globe",
            "year": 2011,
            "last_observation_date": "a value",
            "last_phenophase": "a value",
            "rolled": False,
            "removed": False,
            "obs": True,
        },
    )
    d.write_observation("1", {"individual_id": "2011_1"})

    d.write_individual(
        "2012_2",
        {
            "individual": "2",
            "source": "globe",
            "year": 2012,
            "last_observation_date": "a value",
            "last_phenophase": "a value",
            "rolled": True,
            "removed": False,
            "obs": True,
        },
    )
    d.write_observation("2", {"individual_id": "2012_2"})

    d.write_individual(
        "2012_3",
        {
            "individual": "3",
            "source": "globe",
            "year": 2012,
            "rolled": True,
            "removed": True,
            "obs": False,
        },
    )

    d.write_individual(
        "2012_4",
        {
            "individual": "4",
            "source": "meteoswiss",
            "year": 2012,
            "last_observation_date": "a value",
            "last_phenophase": "a value",
            "rolled": False,
            "removed": False,
            "obs": True,
        },
    )
    d.write_observation("4", {"individual_id": "2012_4"})

    d.write_individual(
        "2012_5",
        {
            "individual": "5",
            "source": "meteoswiss",
            "year": 2012,
            "rolled": False,
            "removed": True,
            "obs": False,
        },
    )
    d.write_observation("5", {"individual_id": "2012_5"})


@pytest.fixture
def current_phenoyear():
    year = 2012
    d.update_phenoyear(year)
    return year


def test_rollover_individuals__roll_amt(setup, current_phenoyear):
    roll_amt = len(list(d.query_individuals("rolled", "==", True).stream()))

    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1
    )

    assert len(roll_individuals) == roll_amt


def test_rollover_individuals__keys(setup, current_phenoyear):
    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1
    )
    assert len(roll_individuals) > 0
    assert (
        individual["id"] == "2013_" + individual["individual"]
        for individual in roll_individuals
    )


def test_rollover_individuals__documents(setup, current_phenoyear):
    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1
    )
    assert len(roll_individuals) > 0
    for individual in roll_individuals:
        assert individual["rolled"], individual
        assert "last_phenophase" not in individual, individual
        assert "last_observation_date" not in individual, individual


def test_rollover_individuals__single_individual(setup, current_phenoyear):
    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1, "3"
    )
    assert len(roll_individuals) == 1
    for individual in roll_individuals:
        assert individual["id"] == f'{current_phenoyear + 1}_{individual["individual"]}'
        assert individual["individual"] == "3"


def test_remove_stale_individuals__removed_amt(setup, current_phenoyear):
    removed_amt = len(list(d.query_individuals("removed", "==", True).stream()))
    stale_individuals = rollover.get_stale_individuals(current_phenoyear)
    assert len(stale_individuals) > 0
    assert len(stale_individuals) == removed_amt, stale_individuals


def test_rollover__individuals_created(setup, current_phenoyear):
    rollover.rollover()
    for individual_doc in d.query_individuals(
        "year", "==", current_phenoyear + 1
    ).stream():
        assert individual_doc.to_dict()["rolled"], individual_doc.to_dict()


def test_rollover__individuals_removed(mocker, setup, current_phenoyear):
    rollover.rollover()
    for individual_doc in d.query_individuals("year", "==", current_phenoyear).stream():
        assert not individual_doc.to_dict()["removed"], individual_doc.to_dict()


def test_rollover__update_year(mocker, setup, current_phenoyear):
    rollover.rollover()
    assert d.get_phenoyear() == current_phenoyear + 1
