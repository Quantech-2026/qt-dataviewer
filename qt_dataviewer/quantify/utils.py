import sys
from datetime import datetime, timedelta

py_311_plus = sys.version_info >= (3, 11)


def tuid_get_time(tuid: str) -> datetime:
    if py_311_plus:
        return datetime.fromisoformat(tuid[:15]) + timedelta(milliseconds=int(tuid[16:19]))
    return datetime.strptime(tuid[:19], "%Y%m%d-%H%M%S-%f")
