# pylint: disable=unused-argument
import pytest

from phenoback.functions import rollover
from phenoback.utils import data as d
from phenoback.utils import firestore as f


def setup_source(source: str, rolled_source: bool):
    d.write_individual(
        f"2011_1_{source}",
        {
            "individual": f"1_{source}",
            "source": source,
            "year": 2011,
            "last_observation_date": "a value",
            "_rolled": False,
            "_remove": False,
        },
    )

    d.write_individual(
        f"2012_2_{source}",
        {
            "individual": f"2_{source}",
            "source": source,
            "year": 2012,
            "last_observation_date": "a value",
            "reprocess": 1,
            "_rolled": rolled_source,
            "_remove": False,
        },
    )

    d.write_individual(
        f"2012_3_{source}",
        {
            "individual": f"3_{source}",
            "source": source,
            "year": 2012,
            "reprocess": 2,
            "_rolled": rolled_source,
            "_remove": True,
        },
    )

    d.write_individual(
        f"2012_4_{source}",
        {
            "individual": f"4_{source}",
            "source": source,
            "year": 2012,
            "last_observation_date": "a value",
            "deveui": f"deveui_4_{source}",
            "sensor": {"foo": "bar"},
            "reprocess": 1,
            "_rolled": rolled_source,
            "_remove": False,
        },
    )

    d.write_individual(
        f"2012_5_{source}",
        {
            "individual": f"5_{source}",
            "source": source,
            "year": 2012,
            "deveui": f"deveui_5_{source}",
            "sensor": {"foo": "bar"},
            "reprocess": 2,
            "_rolled": rolled_source,
            "_remove": False,
        },
    )


@pytest.fixture(autouse=True)
def setup() -> None:
    """
    Setup based on rollover 2012 -> 2013.
    """
    setup_source("globe", True)
    setup_source("meteoswiss", False)
    setup_source("wld", False)
    setup_source("ranger", True)


@pytest.fixture(autouse=True)
def current_phenoyear():
    year = 2012
    d.update_phenoyear(year)
    return year


def get_amt(year: int, field: str = None):
    query = f.collection("individuals").where("year", "==", year)
    if field and field.startswith("_"):
        query = query.where(field, "==", True)
    elif field:
        query = query.order_by(field)
    return len(list(query.stream()))


def test_get_rollover_individuals__roll_amt(current_phenoyear):
    roll_amt = get_amt(current_phenoyear, "_rolled")

    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1
    )

    assert len(roll_individuals) == roll_amt


def test_get_rollover_individuals__keys(current_phenoyear):
    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1
    )
    assert len(roll_individuals) > 0
    assert (
        individual["id"] == "2013_" + individual["individual"]
        for individual in roll_individuals
    )


def test_get_rollover_individuals__documents(current_phenoyear):
    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1
    )
    assert len(roll_individuals) > 0
    for individual in roll_individuals:
        assert individual["_rolled"], individual
        assert "last_phenophase" not in individual, individual
        assert "last_observation_date" not in individual, individual
        assert "reprocess" not in individual, individual


def test_get_rollover_individuals__single_individual(current_phenoyear):
    roll_individuals = rollover.get_rollover_individuals(
        current_phenoyear, current_phenoyear + 1, "2_globe"
    )
    assert len(roll_individuals) == 1
    for individual in roll_individuals:
        assert individual["id"] == f'{current_phenoyear + 1}_{individual["individual"]}'
        assert individual["individual"] == "2_globe"


def test_get_stale_individuals__removed_amt(current_phenoyear):
    removed_amt = get_amt(current_phenoyear, "_remove")
    assert removed_amt > 0

    stale_individuals = rollover.get_stale_individuals(current_phenoyear)

    assert len(stale_individuals) == removed_amt, stale_individuals


def test_rollover__individuals_created(current_phenoyear):
    roll_amt = get_amt(current_phenoyear, "_rolled")
    rollover.rollover()
    rolled_amt = get_amt(current_phenoyear + 1)
    assert roll_amt == rolled_amt


@pytest.mark.skip("Disabled remove individuals on rollover")
def test_rollover__individuals_removed(current_phenoyear):
    individuals_kept_amt = get_amt(current_phenoyear) - get_amt(
        current_phenoyear, "_remove"
    )
    rollover.rollover()
    assert get_amt(current_phenoyear) == individuals_kept_amt


def test_rollover__update_year(current_phenoyear):
    rollover.rollover()
    assert d.get_phenoyear() == current_phenoyear + 1


def test_rollover__sensor_field(current_phenoyear):
    clear_sensor_amt = get_amt(current_phenoyear, "sensor")

    rollover.rollover()

    assert get_amt(current_phenoyear, "sensor") == clear_sensor_amt

    for sensor_doc in (
        d.query_individuals("year", "==", current_phenoyear).order_by("sensor").stream()
    ):
        assert sensor_doc.to_dict()["sensor"] == {}
    for sensor_doc in (
        d.query_individuals("year", "==", current_phenoyear + 1)
        .order_by("sensor")
        .stream()
    ):
        assert sensor_doc.to_dict()["sensor"] == {}


def test_rollover__invalid_source(caperrors):
    setup_source("invalid", False)
    with pytest.raises(ValueError):
        rollover.rollover()
    assert len(caperrors.records) == 1
