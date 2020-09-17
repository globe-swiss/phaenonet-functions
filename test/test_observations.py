import pytest

from phenoback.functions import observation
from datetime import datetime


@pytest.mark.parametrize(
    "new_date, old_date, expected",
    [
        (datetime(2020, 1, 3), datetime(2020, 1, 3), False),
        (datetime(2020, 1, 2), datetime(2020, 1, 3), False),
        (datetime(2020, 1, 4), datetime(2020, 1, 3), True),
    ],
)
def test_update_last_observation_status(mocker, new_date, old_date, expected):
    mocker.patch(
        "phenoback.functions.observation.get_individual",
        return_value={"last_observation_date": old_date},
    )
    mocker.patch("phenoback.functions.observation.update_document")

    assert expected == observation.update_last_observation(
        "ignored", "ignored", new_date
    )


@pytest.mark.parametrize(
    "observation_type, expected", [("station", False), ("individual", True)]
)
def test_update_last_observation_phenophase(mocker, observation_type, expected):
    mocker.patch(
        "phenoback.functions.observation.get_individual",
        return_value={
            "last_observation_date": datetime(2020, 1, 1),
            "type": observation_type,
        },
    )
    update_mock = mocker.patch("phenoback.functions.observation.update_document")

    assert observation.update_last_observation(
        "ignored", "ignored", datetime(2020, 1, 2)
    )
    update_mock.assert_called_once()
    assert ("last_phenophase" in update_mock.call_args[0][2].keys()) == expected


def test_update_last_observation_update_values(mocker):
    mocker.patch(
        "phenoback.functions.observation.get_individual",
        return_value={
            "last_observation_date": datetime(2020, 1, 3),
            "type": "individual",
        },
    )
    update_mock = mocker.patch("phenoback.functions.observation.update_document")

    assert observation.update_last_observation(
        "ignored", "a_phenophase", datetime(2020, 1, 10)
    )
    update_mock.assert_called_once()
    assert update_mock.call_args[0][2]["last_observation_date"] == datetime(2020, 1, 10)
    assert update_mock.call_args[0][2]["last_phenophase"] == "a_phenophase"
