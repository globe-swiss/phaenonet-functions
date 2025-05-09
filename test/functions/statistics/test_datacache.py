import pytest

import phenoback.utils.data as d
from phenoback.functions.statistics import datacache


def add_observation(year, phenophase, comment=None):
    observation = {"year": year, "phenophase": phenophase}
    if comment is not None:
        observation["comment"] = comment
    d.write_observation(None, observation)


@pytest.fixture(autouse=True)
def cache_clear():
    datacache.cache_clear()


@pytest.mark.parametrize(
    "altitude_value, expected",
    [
        (499, "alt1"),
        (500, "alt2"),
        (799, "alt2"),
        (800, "alt3"),
        (999, "alt3"),
        (1000, "alt4"),
        (1199, "alt4"),
        (1200, "alt5"),
    ],
)
def test_get_altitude_grp(mocker, altitude_value, expected):
    individual_id = "test_id"
    mocker.patch(
        "phenoback.utils.data.get_individual",
        return_value={"altitude": altitude_value},
    )

    result = datacache.get_altitude_grp(individual_id)

    assert result == expected
    assert datacache.get_altitude_grp.cache_info().hits == 0


@pytest.mark.parametrize(
    "individual_data, expected_error",
    [
        (None, KeyError),
        ({"some": "attribute"}, ValueError),
        ({"altitude": None}, ValueError),
    ],
)
def test_get_altitude_grp__errors(mocker, individual_data, expected_error):
    individual_id = "test_id"
    mocker.patch("phenoback.utils.data.get_individual", return_value=individual_data)

    with pytest.raises(expected_error):
        datacache.get_altitude_grp(individual_id)


def test_get_altitude_grp__cached(mocker):
    get_individual_mock = mocker.patch(
        "phenoback.utils.data.get_individual", return_value={"altitude": 100}
    )

    datacache.get_altitude_grp("individual_id_1")
    datacache.get_altitude_grp("individual_id_2")
    datacache.get_altitude_grp("individual_id_1")
    datacache.get_altitude_grp("individual_id_2")

    assert get_individual_mock.call_count == 2


def test_get_observations(mocker):
    mocker.patch(
        "phenoback.utils.data.is_actual_observation",
        return_value=True,
    )

    add_observation(1999, "BEA")
    add_observation(1999, "FRB")
    add_observation(2000, "BEA")
    add_observation(2000, "FRB")

    result = datacache.get_observations(2000, {"BEA"})

    assert len(result) == 1
    assert result[0]["year"] == 2000
    assert result[0]["phenophase"] == "BEA"


def test_get_observations__comment_false(mocker):
    mocker.patch(
        "phenoback.utils.data.is_actual_observation",
        return_value=False,
    )

    add_observation(2000, "BEA")
    add_observation(2000, "FRB")

    result = datacache.get_observations(2000, {"BEA"})

    assert len(result) == 0


def test_get_observations__invalid_phenophase(mocker):
    with pytest.raises(ValueError):
        datacache.get_observations(2000, {"xxx"})


def test_get_observations__cached(mocker):
    mocker.patch(
        "phenoback.utils.data.is_actual_observation",
        return_value=True,
    )
    query_observation_spy = mocker.spy(d, "query_observation")

    datacache.get_observations(2000, {"BEA"})
    datacache.get_observations(2001, {"BEA"})
    datacache.get_observations(2000, {"BEA"})
    datacache.get_observations(2001, {"BEA"})

    assert query_observation_spy.call_count == 2
