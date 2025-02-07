import logging
from collections import defaultdict
from datetime import datetime
from functools import cache

import phenoback.utils.data as d
import phenoback.utils.firestore as f

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

_fbr = defaultdict(int)


def main(data, context):  # pylint: disable=unused-argument
    year = data.get("year")
    process_1y_aggregate_statistics(year)


@cache
def get_altitude_grp(individual_id: str) -> str:
    individual = d.get_individual(individual_id)
    _fbr["individuals"] += 1
    if not individual:
        log.error("Individual %s not found to lookup altitude group", individual_id)
        raise KeyError(individual_id)

    altitude = individual.get("altitude")
    if altitude is None:
        log.error("No altitude found for individual %s", individual_id)
        raise ValueError(individual_id)

    if altitude < 500:
        return "alt1"
    elif altitude < 800:
        return "alt2"
    elif altitude < 1000:
        return "alt3"
    elif altitude < 1200:
        return "alt4"
    return "alt5"


def date_to_woy(phenoyear: int, date: datetime) -> int:
    doy = date.timetuple().tm_yday

    # If the date is before the current year, return negative week number
    if date.year < phenoyear:
        return -((365 - doy) // 7 + 1)

    return (doy - 1) // 7 + 1


def get_observations(phenoyear: int):
    result = [
        doc.to_dict() for doc in d.query_observation("year", "==", phenoyear).stream()
    ]
    _fbr["observations"] += len(result)
    return result


def calculate_1y_agg_statistics(observations: list) -> list:
    statistics_result = {}

    for obs in observations:
        try:
            year = obs["year"]
            individual_id = obs["individual_id"]
            species = obs["species"]
            phenophase = obs["phenophase"]
            altitude_grp = get_altitude_grp(individual_id)
            agg_key = f"{year}_{year}_{species}_{altitude_grp}_{phenophase}"

            statistic_doc = statistics_result.setdefault(
                agg_key,
                {
                    "agg_range": 1,
                    "start_year": year,
                    "end_year": year,
                    "species": species,
                    "altitude_grp": altitude_grp,
                    "phenophase": phenophase,
                    "obs_woy": defaultdict(int),
                    "year_obs_sum": defaultdict(int),
                    "agg_obs_sum": 0,
                    "years": 1,
                },
            )

            woy = date_to_woy(year, obs["date"])
            statistic_doc["obs_woy"][str(woy)] += 1
            statistic_doc["year_obs_sum"][str(year)] += 1
            statistic_doc["agg_obs_sum"] += 1
        except (KeyError, TypeError, ValueError) as e:
            # Log the error and continue with the next observation
            log.error(
                "Unexpected error processing observation (skipping) %s: %s", obs, e
            )
    return statistics_result


@cache  # only for initial processing of all years
def get_1y_agg_statistics(start_year: int, end_year: int) -> list:
    """
    Retrieve preprocessed 1-year aggregate statistics for the given year range. (end_year is excluded)
    """
    statistics = []
    for year in range(start_year, end_year):
        log.debug("load stats: %s %s", year, len(statistics))
        query_result = [
            doc.to_dict()
            for doc in d.query_collection("statistics", "end_year", "==", year)
            .where(filter=f.FieldFilter("agg_range", "==", 1))
            .stream()
        ]
        _fbr["statistics"] += len(query_result)
        statistics.extend(query_result)
    log.info(
        "retrieved %i statistics for years %i-%i",
        len(statistics),
        start_year,
        end_year - 1,
    )
    return statistics


def calculate_statistics_aggregates(
    year_agg_statistics: list, year_range_start, year_range_end
) -> dict:
    """
    Take the 1-year aggregate statistics and aggregate them over a range of years. (year_range_end is excluded)
    """
    # Create a defaultdict to store the aggregated results
    agg_statistics_result = {}

    # Iterate over each entry in the statistics
    for year_agg_statistic in year_agg_statistics:
        year = year_agg_statistic["end_year"]
        species = year_agg_statistic["species"]
        altitude_grp = year_agg_statistic["altitude_grp"]
        phenophase = year_agg_statistic["phenophase"]

        # Only process the entries for the years between start_year and end_year
        if year_range_start <= year < year_range_end:
            agg_key = f"{year_range_start}_{year_range_end - 1}_{species}_{altitude_grp}_{phenophase}"

            # Initialize the entry in aggregated_results if not already present
            if agg_key not in agg_statistics_result:
                agg_statistics_result[agg_key] = {
                    "agg_range": year_range_end - year_range_start,
                    "start_year": year_range_start,
                    "end_year": year_range_end - 1,
                    "species": species,
                    "altitude_grp": altitude_grp,
                    "phenophase": phenophase,
                    "obs_woy": defaultdict(int),
                    "year_obs_sum": defaultdict(int),
                    "agg_obs_sum": 0,
                }

            # Aggregate the counts from obs_cnt
            for woy, count in year_agg_statistic["obs_woy"].items():
                agg_statistics_result[agg_key]["obs_woy"][woy] += count

            # Update the years field with the sum for this year
            agg_statistics_result[agg_key]["year_obs_sum"][str(year)] = (
                year_agg_statistic["agg_obs_sum"]
            )
            agg_statistics_result[agg_key]["agg_obs_sum"] += year_agg_statistic[
                "agg_obs_sum"
            ]

    # After the loop, update "years" field with the count of unique years
    for agg_key, data in agg_statistics_result.items():
        data["years"] = len(data["year_obs_sum"])  # Count of unique years with data
        data["valid"] = (  # todo: remove, debug information
            data["years"] == data["agg_range"] and data["agg_obs_sum"] / 20 > 1
        )
    return agg_statistics_result


def process_1y_aggregate_statistics(year: int = None) -> None:
    """
    Process and write the 1-year aggregate statistics for the given year to statistics collection.
    """
    if not year:
        year = d.get_phenoyear()
        _fbr["phenoyear"] += 1
    observations = get_observations(year)
    statistics = calculate_1y_agg_statistics(observations)

    log.info(
        "process weekly statistics for %i: Observations=%i, statistics=%i",
        year,
        len(observations),
        len(statistics),
    )

    for key, data in statistics.items():
        d.write_document("statistics", key, data)


def process_5y_30y_aggregate_statistics(current_year: int) -> None:
    """
    Process and write the 5-year and 30-year aggregates to the statistics collection. (current_year is excluded)
    Invoked on phenoyear roll-over.
    """
    all_stats = get_1y_agg_statistics(current_year - 30, current_year)
    agg5y = calculate_statistics_aggregates(all_stats, current_year - 5, current_year)
    agg30y = calculate_statistics_aggregates(all_stats, current_year - 30, current_year)

    log.info(
        "process aggregate statistics for %i: stats=%i, 5y=%i, 30y=%i",
        current_year,
        len(all_stats),
        len(agg5y),
        len(agg30y),
    )

    for key, data in agg5y.items():
        d.write_document("statistics", key, data)
    for key, data in agg30y.items():
        d.write_document("statistics", key, data)


def get_firebase_reads():
    return _fbr
