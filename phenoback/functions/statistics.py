import logging
from collections import defaultdict
from datetime import datetime
from functools import cache

import phenoback.utils.data as d

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def main(data, context):  # pylint: disable=unused-argument
    process_year_statistics()


@cache
def get_altitude_grp(individual_id: str) -> str:
    individual = d.get_individual(individual_id)
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
    return [
        doc.to_dict() for doc in d.query_observation("year", "==", phenoyear).stream()
    ]


def calculate_statistics(observations: list) -> list:
    statistics = {}

    for obs in observations:
        try:
            year = obs["year"]
            individual_id = obs["individual_id"]
            species = obs["species"]
            phenophase = obs["phenophase"]
            altitude_grp = get_altitude_grp(individual_id)
            key = f"{year}_{species}_{altitude_grp}_{phenophase}"

            observation = statistics.setdefault(
                key,
                {
                    "year": year,
                    "species": species,
                    "altitude_grp": altitude_grp,
                    "phenophase": phenophase,
                    "obs_woy": defaultdict(int),
                    "obs_sum": 0,
                },
            )

            woy = date_to_woy(year, obs["date"])
            observation["obs_woy"][str(woy)] += 1
            observation["obs_sum"] += 1
        except (KeyError, TypeError, ValueError) as e:
            # Log the error and continue with the next observation
            log.error(
                "Unexpected error processing observation (skipping) %s: %s", obs, e
            )
    return statistics


@cache
def get_statistics(start_year: int, end_year: int) -> list:
    statistics = []
    for year in range(start_year, end_year):
        print("load stats:", year, len(statistics))
        statistics.extend(
            [
                doc.to_dict()
                for doc in d.query_collection("statistics", "year", "==", year).stream()
            ]
        )
    log.debug(
        "retrieved %i statistics for years %i-%i", len(statistics), start_year, end_year
    )
    return statistics


def calculate_statistics_aggregates(
    statistics: list, year_range_start, year_range_end
) -> dict:
    # Create a defaultdict to store the aggregated results
    agg_statistics = {}

    # Iterate over each entry in the statistics
    for statistic in statistics:
        year = statistic["year"]
        species = statistic["species"]
        altitude_grp = statistic["altitude_grp"]
        phenophase = statistic["phenophase"]

        # Only process the entries for the years between start_year and end_year
        if year_range_start <= year < year_range_end:
            agg_key = f"{year_range_start}_{year_range_end}_{species}_{altitude_grp}_{phenophase}"

            # Initialize the entry in aggregated_results if not already present
            if agg_key not in agg_statistics:
                agg_statistics[agg_key] = {
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
            for woy, count in statistic["obs_woy"].items():
                agg_statistics[agg_key]["obs_woy"][woy] += count

            # Update the years field with the sum for this year
            agg_statistics[agg_key]["year_obs_sum"][str(year)] += statistic["obs_sum"]
            agg_statistics[agg_key]["agg_obs_sum"] += statistic["obs_sum"]

    # After the loop, update "years" field with the count of unique years
    for agg_key, data in agg_statistics.items():
        data["years"] = len(data["year_obs_sum"])  # Count of unique years with data
        data["valid"] = (  # todo: remove, debug information
            data["years"] == data["agg_range"] and data["agg_obs_sum"] / 20 > 1
        )
    return agg_statistics


def process_year_statistics(year: int = None) -> None:
    if not year:
        year = d.get_phenoyear()
    observations = get_observations(year)
    statistics = calculate_statistics(observations)

    log.debug(
        "process yearly statistics for %i: Observations=%i, statistics=%i",
        year,
        len(observations),
        len(statistics),
    )

    for key, data in statistics.items():
        d.write_document("statistics", key, data)


def process_year_aggregate_statistics(current_year: int) -> None:
    """
    Process the aggregates for the past years not including the current year. Invoked on phenoyear roll-over.
    """
    all_stats = get_statistics(1900, 2024)  # current_year-30
    agg5y = calculate_statistics_aggregates(all_stats, current_year - 5, current_year)
    agg30y = calculate_statistics_aggregates(all_stats, current_year - 30, current_year)

    log.debug(
        "process aggregate statistics for %i: stats=%i, 5y=%i, 30y=%i",
        current_year,
        len(all_stats),
        len(agg5y),
        len(agg30y),
    )

    for key, data in agg5y.items():
        d.write_document("statistics_agg", key, data)
    for key, data in agg30y.items():
        d.write_document("statistics_agg", key, data)
