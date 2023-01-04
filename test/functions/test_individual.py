# pylint: disable=protected-access

from datetime import datetime, timezone

import pytest

import phenoback.utils.data as d
from phenoback.functions import individual as i


@pytest.fixture()
def individual():
    individual_id = "individual_id"
    data = {
        "type": "individual",
        "last_phenophase": "old_pp",
        "last_observation_date": datetime(2019, 1, 1, tzinfo=timezone.utc),
    }
    d.write_individual(individual_id, data)
    return individual_id, data


@pytest.fixture()
def station():
    station_id = "station_id"
    data = {
        "type": "station",
        "last_observation_date": datetime(2019, 1, 1, tzinfo=timezone.utc),
    }
    d.write_individual(station_id, data)
    return station_id, data


def create_last_observation(individual_id):
    d.write_observation(
        "obs_1",
        {
            "individual_id": individual_id,
            "date": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "phenophase": "A",
        },
    )
    d.write_observation(
        "obs_3",
        {
            "individual_id": individual_id,
            "date": datetime(2020, 1, 3, tzinfo=timezone.utc),
            "phenophase": "C",
        },
    )
    d.write_observation(
        "obs_2",
        {
            "individual_id": individual_id,
            "date": datetime(2020, 1, 2, tzinfo=timezone.utc),
            "phenophase": "B",
        },
    )
    return (
        "obs_3",
        {
            "individual_id": individual_id,
            "date": datetime(2020, 1, 3, tzinfo=timezone.utc),
            "phenophase": "C",
        },
    )


def test_update_last_observation__individual(individual):
    last_observation = create_last_observation(individual[0])
    i.updated_observation(individual[0])
    updated_individual = d.get_individual(individual[0])

    assert updated_individual.get("last_observation_date") == last_observation[1].get(
        "date"
    )
    assert updated_individual.get("last_phenophase") == last_observation[1].get(
        "phenophase"
    )


def test_update_last_observation__no_observations(individual):
    i.updated_observation(individual[0])
    updated_individual = d.get_individual(individual[0])
    assert updated_individual.get("last_observation_date") is None
    assert updated_individual.get("last_phenophase") is None


def test_update_last_observation__no_individual(capwarnings):
    i.updated_observation("not_existing_id")
    assert len(capwarnings.records) == 1


def test_update_last_observation__station(station):
    last_observation = create_last_observation(station[0])
    i.updated_observation(station[0])
    updated_station = d.get_individual(station[0])
    assert updated_station.get("last_observation_date") == last_observation[1].get(
        "date"
    )
    assert updated_station.get("last_phenophase") is None


def test_get_last_observation():
    last_observation = create_last_observation("id")
    assert i._get_last_observation("id") == last_observation[1]


def test_get_last_observation__no_observations():
    assert i._get_last_observation("no_observations") is None
