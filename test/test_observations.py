# pylint: disable=protected-access

from datetime import datetime, timezone

import pytest

import phenoback.utils.data as d
from phenoback.functions import observation


@pytest.fixture()
def individual_id():
    d.write_individual(
        "individual_id",
        {
            "type": "individual",
            "last_phenophase": "old_pp",
            "last_observation_date": datetime(2020, 1, 1, tzinfo=timezone.utc),
        },
    )
    return "individual_id"


@pytest.fixture()
def station_id():
    d.write_individual(
        "station_id",
        {
            "type": "station",
            "last_observation_date": datetime(2020, 1, 1, tzinfo=timezone.utc),
        },
    )
    return "station_id"


@pytest.fixture()
def last_observation():
    d.write_observation(
        "obs_1",
        {
            "individual_id": "individual_id",
            "date": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "phenophase": "A",
        },
    )
    d.write_observation(
        "obs_3",
        {
            "individual_id": "individual_id",
            "date": datetime(2020, 1, 3, tzinfo=timezone.utc),
            "phenophase": "C",
        },
    )
    d.write_observation(
        "obs_2",
        {
            "individual_id": "individual_id",
            "date": datetime(2020, 1, 2, tzinfo=timezone.utc),
            "phenophase": "B",
        },
    )
    return (
        "individual_id",
        {
            "individual_id": "individual_id",
            "date": datetime(2020, 1, 3, tzinfo=timezone.utc),
            "phenophase": "C",
        },
    )


@pytest.mark.parametrize(
    "new_date, old_date, update_expected",
    [
        (
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2020, 1, 2, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            False,
        ),
        (
            datetime(2020, 1, 4, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            True,
        ),
    ],
)
def test_update_last_observation__individual(
    individual_id, new_date, old_date, update_expected
):
    d.update_individual(individual_id, {"last_observation_date": old_date})

    assert update_expected == observation.updated_observation(
        individual_id, "new_pp", new_date
    )
    updated_individual = d.get_individual(individual_id)
    assert (
        updated_individual.get("last_observation_date") == new_date
        if update_expected
        else old_date
    )
    assert (
        updated_individual.get("last_phenophase") == "new_pp"
        if update_expected
        else "old_pp"
    )


@pytest.mark.parametrize(
    "new_date, old_date, update_expected",
    [
        (
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2020, 1, 2, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            False,
        ),
        (
            datetime(2020, 1, 4, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            True,
        ),
    ],
)
def test_update_last_observation__station(
    station_id, new_date, old_date, update_expected
):
    d.update_individual(station_id, {"last_observation_date": old_date})

    assert update_expected == observation.updated_observation(
        station_id, "new_pp", new_date
    )
    updated_station = d.get_individual(station_id)
    assert (
        updated_station.get("last_observation_date") == new_date
        if update_expected
        else old_date
    )
    assert updated_station.get("last_phenophase") is None


@pytest.mark.parametrize(
    "current_last_observation_date, removed_last_observation_date, update_expected",
    [
        (
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2020, 1, 2, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            False,
        ),
        (
            datetime(2020, 1, 4, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            False,
        ),
    ],
)
def test_removed_observation(
    mocker,
    individual_id,
    current_last_observation_date,
    removed_last_observation_date,
    update_expected,
):
    new_last_observation = {
        "date": datetime(2022, 1, 1, tzinfo=timezone.utc),
        "phenophase": "new_pp",
    }
    mocker.patch(
        "phenoback.functions.observation._get_last_observation",
        return_value=new_last_observation,
    )
    d.update_individual(
        individual_id, {"last_observation_date": current_last_observation_date}
    )

    assert update_expected == observation.removed_observation(
        individual_id, removed_last_observation_date
    )
    updated_individual = d.get_individual(individual_id)
    assert (
        updated_individual.get("last_observation_date")
        == new_last_observation.get("date")
        if update_expected
        else current_last_observation_date
    )
    assert (
        updated_individual.get("last_phenophase") == "new_pp"
        if update_expected
        else "old_pp"
    )


def test_removed_observation__no_observations(mocker, individual_id):
    new_last_observation = None
    current_last_observation_date = datetime(2020, 1, 3, tzinfo=timezone.utc)
    removed_last_observation_date = datetime(2020, 1, 3, tzinfo=timezone.utc)
    mocker.patch(
        "phenoback.functions.observation._get_last_observation",
        return_value=new_last_observation,
    )
    d.update_individual(
        individual_id, {"last_observation_date": current_last_observation_date}
    )

    assert observation.removed_observation(individual_id, removed_last_observation_date)
    updated_individual = d.get_individual(individual_id)
    assert updated_individual.get("last_observation_date") is None
    assert updated_individual.get("last_phenophase") is None


def test_get_last_observation(last_observation):
    print(last_observation[0])
    assert observation._get_last_observation(last_observation[0]) == last_observation[1]


def test_get_last_observation__no_observations():
    assert observation._get_last_observation("no_observations") is None
