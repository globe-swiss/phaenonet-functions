import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.functions.statistics import datacache

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

ANALYTIC_PHENOPHASES = {"BEA", "BLA", "BFA", "BVA", "FRA"}


def main(data, context):  # pylint: disable=unused-argument
    year = data["year"] if "year" in data else d.get_phenoyear()
    process_yearly_statistics(year)


def process_yearly_statistics(year: int) -> None:
    """
    Process yearly statistics for the given year.
    """
    observations = datacache.get_observations(year, ANALYTIC_PHENOPHASES)
    species_statistics = get_species_statistics(observations)
    altitude_statistics = get_altitude_statistics(observations)

    log.info(
        "Write %i species statistics for phenoyear %i processing %i observations",
        len(species_statistics),
        year,
        len(observations),
    )
    f.write_batch("statistics_yearly_species", "id", d.to_id_array(species_statistics))
    log.info(
        "Write %i altitude statistics for phenoyear %i processing %i observations",
        len(species_statistics),
        year,
        len(observations),
    )
    f.write_batch(
        "statistics_yearly_altitude", "id", d.to_id_array(altitude_statistics)
    )


def get_species_statistics(observations: list[Any]) -> dict:
    phase_dates: dict[str, dict[str, Any]] = defaultdict(
        lambda: defaultdict(list[datetime])
    )

    for obs in observations:
        year = obs["year"]
        species = obs["species"]
        source = obs["source"]
        phenophase = obs["phenophase"]
        observation_date = obs["date"]

        phase_dates[f"{year}_{species}_all"][phenophase].append(observation_date)
        phase_dates[f"{year}_{species}_{source}"][phenophase].append(observation_date)

    results: dict[str, dict[str, Any]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list[datetime]))
    )
    for key, phases in phase_dates.items():
        year, species, source = key.split("_")
        results[key]["year"] = year
        results[key]["species"] = species
        results[key]["source"] = source
        for phenophase, observation_dates in phases.items():
            results[key]["data"][phenophase] = get_statistic_values(observation_dates)

    if not results:
        raise ValueError(
            f"No statistics could be calculate using {len(observations)} observations"
        )

    return results


def get_altitude_statistics(observations: list[Any]) -> dict:
    alt_dates: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list[datetime]))
    )

    for obs in observations:
        year = obs["year"]
        species = obs["species"]
        source = obs["source"]
        altitude_grp = datacache.get_altitude_grp(obs["individual_id"])
        phenophase = obs["phenophase"]
        observation_date = obs["date"]

        alt_dates[f"{year}_{species}_all"][phenophase][altitude_grp].append(
            observation_date
        )
        alt_dates[f"{year}_{species}_{source}"][phenophase][altitude_grp].append(
            observation_date
        )

    results: dict[str, dict[str, Any]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list[datetime])))
    )
    for key, phases in alt_dates.items():
        year, species, source = key.split("_")
        results[key]["year"] = year
        results[key]["species"] = species
        results[key]["source"] = source
        for phenophase, alt_grp in phases.items():
            for alt_grp, observation_dates in alt_grp.items():
                results[key]["data"][phenophase][alt_grp] = get_statistic_values(
                    observation_dates
                )

    if not results:
        raise ValueError(
            f"No statistics could be calculate from {len(observations)} observations"
        )

    return results


def get_statistic_values(observation_dates: list) -> dict[str, Any]:
    # should never be balled with empty list
    return {
        "min": np.min(observation_dates),
        "max": np.max(observation_dates),
        "median": np.quantile(observation_dates, 0.5, method="nearest"),
        "quantile_25": np.quantile(observation_dates, 0.25, method="nearest"),
        "quantile_75": np.quantile(observation_dates, 0.75, method="nearest"),
        "obs_sum": len(observation_dates),
    }
