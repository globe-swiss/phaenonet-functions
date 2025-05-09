from datetime import datetime

import pytest

from phenoback.functions.statistics import yearly


def od(species, source, phenophase, individual_id="test_id"):
    return {
        "individual_id": individual_id,
        "year": "2023",
        "species": species,
        "source": source,
        "phenophase": phenophase,
        "date": datetime(2023, 4, 15),
    }


def test_main(mocker, data, context):
    data["year"] = 2000
    process_yearly_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.yearly.process_yearly_statistics"
    )
    mocker.patch("phenoback.utils.data.get_phenoyear", return_value=2001)

    yearly.main(data, context)

    process_yearly_statistics_mock.assert_called_once_with(data["year"])


def test_main__year(mocker, data, context):
    year = 2000
    process_yearly_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.yearly.process_yearly_statistics"
    )
    mocker.patch("phenoback.utils.data.get_phenoyear", return_value=year)

    yearly.main(data, context)

    process_yearly_statistics_mock.assert_called_once_with(year)


def test_process_yearly_statistics(mocker):
    year = 2000
    observations = "observations_return_values"
    species_statistics = "species_statistics_return_values"
    altitude_statistics = "altitude_statistics_return_values"
    get_observations_mock = mocker.patch(
        "phenoback.functions.statistics.datacache.get_observations",
        return_value=observations,
    )
    get_species_statitics_mock = mocker.patch(
        "phenoback.functions.statistics.yearly.get_species_statistics",
        return_value=species_statistics,
    )
    get_altitude_statitics_mock = mocker.patch(
        "phenoback.functions.statistics.yearly.get_altitude_statistics",
        return_value=altitude_statistics,
    )
    to_id_array_mock = mocker.patch("phenoback.utils.data.to_id_array")
    write_batch_mock = mocker.patch("phenoback.utils.firestore.write_batch")

    yearly.process_yearly_statistics(year)

    get_observations_mock.assert_called_once_with(year, yearly.ANALYTIC_PHENOPHASES)
    get_species_statitics_mock.assert_called_once_with(observations)
    get_altitude_statitics_mock.assert_called_once_with(observations)

    assert to_id_array_mock.call_count == 2
    to_id_array_mock.assert_any_call(species_statistics)
    to_id_array_mock.assert_any_call(altitude_statistics)

    assert write_batch_mock.call_count == 2
    write_batch_mock.assert_any_call("statistics_yearly_species", "id", mocker.ANY)
    write_batch_mock.assert_any_call("statistics_yearly_altitude", "id", mocker.ANY)


def test_get_species_statistics():
    test_observations = [
        od("species1", "source1", "phase1"),
        od("species1", "source1", "phase1"),
        od("species1", "source2", "phase1"),
        od("species1", "source2", "phase2"),
        od("species2", "source1", "phase1"),
    ]

    result = yearly.get_species_statistics(test_observations)

    assert len(result) == 5, result.keys()

    assert len(result["2023_species1_all"]["data"]) == 2
    assert result["2023_species1_all"]["data"]["phase1"]["obs_sum"] == 3
    assert result["2023_species1_all"]["data"]["phase2"]["obs_sum"] == 1

    assert len(result["2023_species1_source1"]["data"]) == 1
    assert result["2023_species1_source1"]["data"]["phase1"]["obs_sum"] == 2

    assert len(result["2023_species1_source2"]["data"]) == 2
    assert result["2023_species1_source2"]["data"]["phase1"]["obs_sum"] == 1
    assert result["2023_species1_source2"]["data"]["phase2"]["obs_sum"] == 1

    assert len(result["2023_species2_all"]["data"]) == 1
    assert result["2023_species2_all"]["data"]["phase1"]["obs_sum"] == 1

    assert len(result["2023_species2_source1"]["data"]) == 1
    assert result["2023_species2_source1"]["data"]["phase1"]["obs_sum"] == 1


def test_get_species_statistics__no_observations():
    with pytest.raises(ValueError):
        yearly.get_species_statistics([])


def test_get_altitude_statistics(mocker):
    test_observations = [
        od("species1", "source1", "phase1", "alt1"),
        od("species1", "source1", "phase1", "alt1"),
        od("species1", "source2", "phase1", "alt1"),
        od("species1", "source2", "phase2", "alt1"),
        od("species2", "source1", "phase1", "alt1"),
        od("species1", "source1", "phase1", "alt2"),
        od("species1", "source2", "phase1", "alt2"),
    ]
    # each individual_id is treated as separate altitude_grp
    mocker.patch(
        "phenoback.functions.statistics.datacache.get_altitude_grp",
        side_effect=lambda individual_id: individual_id,
    )

    result = yearly.get_altitude_statistics(test_observations)

    assert len(result) == 5, result.keys()

    # Test species 1, all sources aggregation
    assert len(result["2023_species1_all"]["data"]) == 2  # num phases
    assert len(result["2023_species1_all"]["data"]["phase1"]) == 2  # num alt grps
    assert len(result["2023_species1_all"]["data"]["phase2"]) == 1  # num alt grps
    assert result["2023_species1_all"]["data"]["phase1"]["alt1"]["obs_sum"] == 3
    assert result["2023_species1_all"]["data"]["phase1"]["alt2"]["obs_sum"] == 2
    assert result["2023_species1_all"]["data"]["phase2"]["alt1"]["obs_sum"] == 1

    # Test species1, source1 specific
    assert len(result["2023_species1_source1"]["data"]) == 1  # num phases
    assert len(result["2023_species1_source1"]["data"]["phase1"]) == 2  # num alt grps
    assert result["2023_species1_source1"]["data"]["phase1"]["alt1"]["obs_sum"] == 2
    assert result["2023_species1_source1"]["data"]["phase1"]["alt2"]["obs_sum"] == 1

    # Test species1, source2 specific
    assert len(result["2023_species1_source2"]["data"]) == 2  # num phases
    assert len(result["2023_species1_source2"]["data"]["phase1"]) == 2  # num alt grps
    assert len(result["2023_species1_source2"]["data"]["phase2"]) == 1  # num alt grps
    assert result["2023_species1_source2"]["data"]["phase1"]["alt1"]["obs_sum"] == 1
    assert result["2023_species1_source2"]["data"]["phase1"]["alt2"]["obs_sum"] == 1
    assert result["2023_species1_source2"]["data"]["phase2"]["alt1"]["obs_sum"] == 1

    # Test species2
    assert len(result["2023_species2_all"]["data"]) == 1  # num phases
    assert len(result["2023_species2_all"]["data"]["phase1"]) == 1  # num alt grps
    assert result["2023_species2_all"]["data"]["phase1"]["alt1"]["obs_sum"] == 1

    assert len(result["2023_species2_source1"]["data"]) == 1  # num phases
    assert len(result["2023_species2_source1"]["data"]["phase1"]) == 1  # num alt grps
    assert result["2023_species2_source1"]["data"]["phase1"]["alt1"]["obs_sum"] == 1


def test_get_altitude_statistics__no_observations():
    with pytest.raises(ValueError):
        yearly.get_altitude_statistics([])


def test_get_statistic_values():
    test_dates = [
        datetime(2023, 4, 10),
        datetime(2023, 4, 15),
        datetime(2023, 4, 20),
        datetime(2023, 4, 25),
        datetime(2023, 4, 30),
    ]

    result = yearly.get_statistic_values(test_dates)

    assert result["min"] == datetime(2023, 4, 10)
    assert result["max"] == datetime(2023, 4, 30)
    assert result["median"] == datetime(2023, 4, 20)
    assert result["quantile_25"] == datetime(2023, 4, 15)
    assert result["quantile_75"] == datetime(2023, 4, 25)
    assert result["obs_sum"] == 5


def test_get_statistic_values__single_date():
    test_date = [datetime(2023, 4, 15)]

    result = yearly.get_statistic_values(test_date)

    assert result["min"] == datetime(2023, 4, 15)
    assert result["max"] == datetime(2023, 4, 15)
    assert result["median"] == datetime(2023, 4, 15)
    assert result["quantile_25"] == datetime(2023, 4, 15)
    assert result["quantile_75"] == datetime(2023, 4, 15)
    assert result["obs_sum"] == 1


def test_get_statistic_values__no_values():
    with pytest.raises(ValueError):
        yearly.get_statistic_values([])
