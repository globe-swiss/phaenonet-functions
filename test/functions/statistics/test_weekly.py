from datetime import datetime

import pytest

import phenoback.utils.firestore as f
from phenoback.functions.statistics import weekly


def test_main(mocker, data, context):
    data["year"] = 2000
    process_1y_aggregate_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.process_1y_aggregate_statistics"
    )
    mocker.patch("phenoback.utils.data.get_phenoyear", return_value=2001)

    weekly.main(data, context)

    process_1y_aggregate_statistics_mock.assert_called_once_with(data["year"])


def test_main__year(mocker, data, context):
    year = 2000
    process_1y_aggregate_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.process_1y_aggregate_statistics"
    )
    mocker.patch("phenoback.utils.data.get_phenoyear", return_value=year)

    weekly.main(data, context)

    process_1y_aggregate_statistics_mock.assert_called_once_with(year)


@pytest.mark.parametrize(
    "year, date, expected",
    [
        (2000, datetime(2000, 1, 1), 1),
        (2000, datetime(2000, 1, 7), 1),
        (2000, datetime(2000, 1, 8), 2),
        (2000, datetime(2000, 12, 31), 53),
        (2000, datetime(1999, 12, 31), -1),
        (2000, datetime(1999, 12, 25), -1),
        (2000, datetime(1999, 12, 24), -2),
    ],
)
def test_date_to_woy(year, date, expected):
    result = weekly.date_to_woy(year, date)

    assert result == expected


def test_write_statistics():
    data = {"id1": {"foo1": "bar1"}, "id2": {"foo2": "bar2"}}

    weekly.write_statistics(data)

    num_docs = 0
    for doc in f.collection("statistics").stream():
        assert doc.to_dict() == data[doc.id]
        num_docs += 1
    assert num_docs == 2


def test_calculate_1y_agg_statistics(mocker):
    mocker.patch(
        "phenoback.functions.statistics.datacache.get_altitude_grp", return_value="alt1"
    )
    observations = [
        {
            "year": 2000,
            "individual_id": "1",
            "species": "foo",
            "phenophase": "BEA",
            "date": datetime(2000, 1, 1),
        },
        {
            "year": 2000,
            "individual_id": "2",
            "species": "foo",
            "phenophase": "BEA",
            "date": datetime(2000, 1, 3),
        },
        {
            "year": 2000,
            "individual_id": "2",
            "species": "foo",
            "phenophase": "BEA",
            "date": datetime(2000, 1, 9),
        },
        {
            "year": 2000,
            "individual_id": "1",
            "species": "foo",
            "phenophase": "FRB",
            "date": datetime(2000, 1, 1),
        },
        {
            "year": 2001,
            "individual_id": "1",
            "species": "foo",
            "phenophase": "BEA",
            "date": datetime(2001, 1, 9),
        },
    ]

    result = weekly.calculate_1y_agg_statistics(observations)

    assert len(result) == 3

    assert result["2000_2000_foo_alt1_BEA"]["display_year"] == 2000
    assert result["2000_2000_foo_alt1_BEA"]["agg_range"] == 1
    assert result["2000_2000_foo_alt1_BEA"]["start_year"] == 2000
    assert result["2000_2000_foo_alt1_BEA"]["end_year"] == 2000
    assert result["2000_2000_foo_alt1_BEA"]["species"] == "foo"
    assert result["2000_2000_foo_alt1_BEA"]["altitude_grp"] == "alt1"
    assert result["2000_2000_foo_alt1_BEA"]["phenophase"] == "BEA"
    assert result["2000_2000_foo_alt1_BEA"]["obs_woy"] == {"1": 2, "2": 1}
    assert result["2000_2000_foo_alt1_BEA"]["year_obs_sum"] == {"2000": 3}
    assert result["2000_2000_foo_alt1_BEA"]["agg_obs_sum"] == 3
    assert result["2000_2000_foo_alt1_BEA"]["years"] == 1

    assert result["2000_2000_foo_alt1_FRB"]["display_year"] == 2000
    assert result["2000_2000_foo_alt1_FRB"]["agg_range"] == 1
    assert result["2000_2000_foo_alt1_FRB"]["start_year"] == 2000
    assert result["2000_2000_foo_alt1_FRB"]["end_year"] == 2000
    assert result["2000_2000_foo_alt1_FRB"]["species"] == "foo"
    assert result["2000_2000_foo_alt1_FRB"]["altitude_grp"] == "alt1"
    assert result["2000_2000_foo_alt1_FRB"]["phenophase"] == "FRB"
    assert result["2000_2000_foo_alt1_FRB"]["obs_woy"] == {"1": 1}
    assert result["2000_2000_foo_alt1_FRB"]["year_obs_sum"] == {"2000": 1}
    assert result["2000_2000_foo_alt1_FRB"]["agg_obs_sum"] == 1
    assert result["2000_2000_foo_alt1_FRB"]["years"] == 1

    assert result["2001_2001_foo_alt1_BEA"]["display_year"] == 2001
    assert result["2001_2001_foo_alt1_BEA"]["agg_range"] == 1
    assert result["2001_2001_foo_alt1_BEA"]["start_year"] == 2001
    assert result["2001_2001_foo_alt1_BEA"]["end_year"] == 2001
    assert result["2001_2001_foo_alt1_BEA"]["species"] == "foo"
    assert result["2001_2001_foo_alt1_BEA"]["altitude_grp"] == "alt1"
    assert result["2001_2001_foo_alt1_BEA"]["phenophase"] == "BEA"
    assert result["2001_2001_foo_alt1_BEA"]["obs_woy"] == {"2": 1}
    assert result["2001_2001_foo_alt1_BEA"]["year_obs_sum"] == {"2001": 1}
    assert result["2001_2001_foo_alt1_BEA"]["agg_obs_sum"] == 1
    assert result["2001_2001_foo_alt1_BEA"]["years"] == 1


@pytest.mark.parametrize(
    "start_year, end_year, expected",
    [
        (2000, 2000, 0),
        (2000, 2001, 2),
        (2000, 2002, 3),
    ],
)
def test_get_1y_agg_statistics(start_year, end_year, expected):
    f.write_document(
        "statistics",
        "1999_1",
        {
            "start_year": 1999,
            "end_year": 1999,
            "agg_range": 1,
            "phenophase": "BEA",
        },
    )
    f.write_document(
        "statistics",
        "2000_1",
        {
            "start_year": 2000,
            "end_year": 2000,
            "agg_range": 1,
            "phenophase": "BEA",
        },
    )
    f.write_document(
        "statistics",
        "2000_2",
        {
            "start_year": 2000,
            "end_year": 2000,
            "agg_range": 1,
            "phenophase": "FRA",
        },
    )
    f.write_document(
        "statistics",
        "2001_1",
        {
            "start_year": 2001,
            "end_year": 2001,
            "agg_range": 1,
            "phenophase": "BEA",
        },
    )
    f.write_document(
        "statistics",
        "discard",
        {
            "start_year": 1990,
            "end_year": 2000,
            "agg_range": 10,
            "phenophase": "BEA",
        },
    )

    result = weekly.get_1y_agg_statistics(start_year, end_year)

    assert len(result) == expected
    for statistic_content in result:
        assert len(statistic_content) == 4


def test_calculate_statistics_aggregates():
    year_agg_statistics = [
        {
            "end_year": 2000,
            "species": "foo",
            "altitude_grp": "alt1",
            "phenophase": "BEA",
            "obs_woy": {"1": 2, "2": 1},
            "agg_obs_sum": 3,
        },
        {
            "end_year": 2000,
            "species": "foo",
            "altitude_grp": "alt1",
            "phenophase": "FRB",
            "obs_woy": {"1": 1},
            "agg_obs_sum": 1,
        },
        {
            "end_year": 2001,
            "species": "foo",
            "altitude_grp": "alt1",
            "phenophase": "BEA",
            "obs_woy": {"2": 4},
            "agg_obs_sum": 4,
        },
    ]

    result = weekly.calculate_statistics_aggregates(year_agg_statistics, 1995, 2005)

    assert len(result) == 2
    assert result["1995_2004_foo_alt1_BEA"]["display_year"] == 2005
    assert result["1995_2004_foo_alt1_BEA"]["agg_range"] == 10
    assert result["1995_2004_foo_alt1_BEA"]["start_year"] == 1995
    assert result["1995_2004_foo_alt1_BEA"]["end_year"] == 2004
    assert result["1995_2004_foo_alt1_BEA"]["species"] == "foo"
    assert result["1995_2004_foo_alt1_BEA"]["altitude_grp"] == "alt1"
    assert result["1995_2004_foo_alt1_BEA"]["phenophase"] == "BEA"
    assert result["1995_2004_foo_alt1_BEA"]["obs_woy"] == {"1": 2, "2": 5}
    assert result["1995_2004_foo_alt1_BEA"]["year_obs_sum"] == {"2000": 3, "2001": 4}
    assert result["1995_2004_foo_alt1_BEA"]["agg_obs_sum"] == 7
    assert result["1995_2004_foo_alt1_BEA"]["years"] == 2


def test_process_1y_aggregate_statistics(mocker, phenoyear):
    observations_return = ["observation1", "observation2"]
    statistics_return = {"statistic1": "statistic1", "statistic2": "statistic2"}
    get_observations_mock = mocker.patch(
        "phenoback.functions.statistics.datacache.get_observations",
        return_value=observations_return,
    )
    calculate_1y_agg_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.calculate_1y_agg_statistics",
        return_value=statistics_return,
    )
    write_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.write_statistics"
    )

    weekly.process_1y_aggregate_statistics(phenoyear)

    get_observations_mock.assert_called_once_with(
        phenoyear, weekly.STATISTIC_PHENOPHASES
    )
    calculate_1y_agg_statistics_mock.assert_called_once_with(observations_return)
    write_statistics_mock.assert_called_once_with(statistics_return)


def test_process_1y_aggregate_statistics__year_default(mocker):
    get_observations_mock = mocker.patch(
        "phenoback.functions.statistics.datacache.get_observations"
    )
    mocker.patch("phenoback.functions.statistics.weekly.calculate_1y_agg_statistics")
    mocker.patch("phenoback.functions.statistics.weekly.write_statistics")

    weekly.process_1y_aggregate_statistics(1234)

    get_observations_mock.assert_called_once_with(1234, weekly.STATISTIC_PHENOPHASES)


def test_30y_aggregate_statistics(mocker):
    current_year = 2000
    statistics_return = ["statistics1", "statistics2"]
    aggregates_5y_return = {"5y_1": "aggregate1", "5y_2": "aggregate2"}
    aggregates_30y_return = {"30y_1": "aggregate1", "30y_2": "aggregate2"}
    get_1y_agg_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.get_1y_agg_statistics",
        return_value=statistics_return,
    )
    calculate_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.calculate_statistics_aggregates",
        side_effect=[aggregates_5y_return, aggregates_30y_return],
    )
    write_statistics_mock = mocker.patch(
        "phenoback.functions.statistics.weekly.write_statistics"
    )

    weekly.process_5y_30y_aggregate_statistics(current_year)

    get_1y_agg_statistics_mock.assert_called_once_with(current_year - 30, current_year)
    assert calculate_statistics_mock.call_count == 2
    calculate_statistics_mock.assert_any_call(
        statistics_return, current_year - 30, current_year
    )
    calculate_statistics_mock.assert_any_call(
        statistics_return, current_year - 5, current_year
    )
    assert write_statistics_mock.call_count == 2
    write_statistics_mock.assert_any_call(aggregates_5y_return)
    write_statistics_mock.assert_any_call(aggregates_30y_return)
