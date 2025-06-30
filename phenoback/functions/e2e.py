import datetime
import logging
from http import HTTPStatus

from dateutil.relativedelta import relativedelta
from flask import Request, Response

import phenoback.utils.data as d
import phenoback.utils.firestore as f
from phenoback.functions import phenorangers, users  # exception: allow functions import

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def main_reset(request: Request):  # pylint: disable=unused-argument
    """
    Clear all individuals for the e2e test user. This is used for assuring the firestore state before running e2e tests.
    """
    delete_user_data(["q7lgBm5nm7PUkof20UdZ9D4d0CV2", "JIcn8kFpI4fYYcbdi9QzPlrHomn1"])
    return Response("ok", HTTPStatus.OK)


def main_restore(request: Request):  # pylint: disable=unused-argument
    """
    Restore test users after database copyback
    """
    restore_test_users()
    restore_sensor_test_data()
    return Response("ok", HTTPStatus.OK)


def delete_user_data(user_ids: list[str]) -> None:
    log.info("Delete all data for %s", user_ids)
    f.delete_batch("observations", "user", "in", user_ids)
    f.delete_batch("individuals", "user", "in", user_ids)
    f.delete_batch("invites", "user", "in", user_ids)
    for user_id in user_ids:
        f.write_document(
            "users",
            user_id,
            {
                "following_individuals": f.DELETE_FIELD,
                "following_users": f.DELETE_FIELD,
            },
            merge=True,
        )


def restore_test_users() -> None:
    d.create_user(
        "q7lgBm5nm7PUkof20UdZ9D4d0CV2",
        "e2e-test-nick",
        "e2e-name",
        "e2e-surname",
        "de-CH",
    )
    users.process_new_user("q7lgBm5nm7PUkof20UdZ9D4d0CV2", "e2e-test-nick")
    d.create_user(
        "JIcn8kFpI4fYYcbdi9QzPlrHomn1",
        "e2e-ranger-nick",
        "e2e-ranger-name",
        "e2e-ranger-surname",
        "de-CH",
    )
    users.process_new_user("JIcn8kFpI4fYYcbdi9QzPlrHomn1", "e2e-ranger-nick")
    phenorangers.set_ranger("JIcn8kFpI4fYYcbdi9QzPlrHomn1")
    d.create_user(
        "3NOG91ip31ZdzdIjEdhaoA925U72",
        "ranger-demo",
    )
    users.process_new_user("3NOG91ip31ZdzdIjEdhaoA925U72", "ranger-demo")
    phenorangers.set_ranger("3NOG91ip31ZdzdIjEdhaoA925U72")


def restore_sensor_test_data() -> None:
    year = 2018
    data = (
        generate_sensor_data(
            monthdates(datetime.date(year - 1, 12, 1), 1), 1, 0, 40, 50, 100
        )
        | generate_sensor_data(quarterdates(year, 1), 1, -20, -10, 0, 25)
        | generate_sensor_data(quarterdates(year, 2), 2, -10, 0, 25, 50)
        | generate_sensor_data(quarterdates(year, 3), 3, 0, 10, 50, 75)
        | generate_sensor_data(quarterdates(year, 4), 4, 10, 20, 75, 100)
    )
    f.write_document("sensors", f"{year}_721", {"data": data, "year": year})
    d.update_individual(f"{year}_721", {"sensor": []})
    d.update_observation(f"721_{year}_HS_BEA", {"date": firebasedate(year - 1, 12, 15)})
    d.update_observation(f"721_{year}_HS_BES", {"date": firebasedate(year, 2, 1)})
    d.update_observation(f"721_{year}_HS_BFA", {"date": firebasedate(year, 3, 1)})
    d.update_observation(f"721_{year}_HS_BLA", {"date": firebasedate(year, 5, 1)})
    d.update_observation(f"721_{year}_HS_BLB", {"date": firebasedate(year, 6, 1)})
    d.update_observation(f"721_{year}_HS_BLE", {"date": firebasedate(year, 7, 1)})
    d.update_observation(f"721_{year}_HS_BVA", {"date": firebasedate(year, 8, 1)})
    d.update_observation(f"721_{year}_HS_BVS", {"date": firebasedate(year, 9, 1)})
    d.update_observation(f"721_{year}_HS_FRA", {"date": firebasedate(year, 10, 1)})
    d.update_observation(f"721_{year}_HS_FRB", {"date": firebasedate(year, 11, 1)})
    d.update_observation(f"721_{year}_HS_KNS", {"date": firebasedate(year, 12, 1)})
    d.update_observation(f"721_{year}_HS_KNV", {"date": firebasedate(year, 12, 15)})


def monthdates(basedt: datetime.date, months: int) -> list[datetime.date]:
    """
    Generate a list of dates for a given number of months starting from a base date.

    Args:
        basedt: The starting date
        months: Number of months to generate dates for

    Returns:
        List of datetime.date objects for each day in the specified month range
    """
    curr = basedt
    result = []
    while curr < basedt + relativedelta(months=+months):
        result.append(curr)
        curr = curr + relativedelta(days=+1)
    return result


def quarterdates(year: int, quarter: int) -> list[datetime.date]:
    basedt = datetime.date(year, quarter * 3 - 2, 1)
    return monthdates(basedt, 3)


def generate_sensor_data(
    dates: list[datetime.date], n: int, at: float, st: float, ah: float, sh: float
) -> dict[str, dict[str, float]]:
    return {
        date.isoformat(): {
            "n": n,
            "ats": at * n,
            "sts": st * n,
            "ahs": ah * n,
            "shs": sh * n,
        }
        for date in dates
    }


def firebasedate(year: int, month: int, day: int) -> datetime.datetime:
    return d.localtime(datetime.datetime(year, month, day))
