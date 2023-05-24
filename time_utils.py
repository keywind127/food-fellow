from datetime import datetime, timezone 
from typing import * 

class TimeStamp:

    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

    @classmethod
    def current_time(class_) -> datetime:

        # obtain current time (in UTC), format it into timestamp, then parse it
        #   Note: This is done so arithmetic operations could be allowed.
        return class_.string2time(class_.time2string(datetime.now(timezone.utc)))

    @classmethod
    def time2string(class_, time_object : datetime) -> str:

        # format time object into timestamp
        return time_object.strftime(class_.TIMESTAMP_FORMAT)

    @classmethod 
    def string2time(class_, time_string : str) -> datetime:

        # parse timestamp into time object
        return datetime.strptime(time_string, class_.TIMESTAMP_FORMAT)