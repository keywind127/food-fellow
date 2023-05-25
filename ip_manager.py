from pymongo.database import Database
from bson.objectid import ObjectId
from time_utils import TimeStamp
from typing import *

class IPRecord(dict):

    def __init__(self, ip_address : str, is_failure : bool, timestamp : Optional[ str ] = None) -> None:

        super(IPRecord, self).__init__()

        # set timestamp to current time if unspecified
        if (timestamp is None):
            timestamp = TimeStamp.time2string(TimeStamp.current_time())

        # pack record data into dictionary
        self.update({
            "ip-address" : ip_address, 
            "is-failure" : is_failure,
            "timestamp"  : timestamp
        })

class IPManager:

    # IP record collection name
    _IP_COLLECTION_NAME = "ip-history"

    # IP blacklist collection name
    _IP_COLLECTION_BLACKLIST_NAME = "ip-blacklist"

    # backtrace period (in seconds)
    _FAILURE_BACKTRACE_PERIOD = 3600

    def __init__(self, database : Database) -> None:

        # Food-Fellow (MongoDB) database object
        self.database = database 

        # collection containing IP records
        #self.collection = self.database[self._IP_COLLECTION_NAME]
        self.collection = getattr(self.database.db, self._IP_COLLECTION_NAME)

        # collection containing blacklisted IPs
        #self.blacklist = self.database[self._IP_COLLECTION_BLACKLIST_NAME]
        self.blacklist = getattr(self.database.db, self._IP_COLLECTION_BLACKLIST_NAME)

    def ip_blacklisted(self, ip_address : str) -> bool:

        # whether specified IP address is blacklisted
        return (self.blacklist.find_one({ "ip-address" : ip_address }) is not None)

    def blacklist_ip(self, ip_address : str) -> None:

        # blacklist specified IP address
        self.blacklist.insert_one(document = { "ip-address" : ip_address })

    def add_record(self, ip_record : IPRecord) -> None:

        assert isinstance(ip_record, IPRecord)

        # insert new record
        self.collection.insert_one(ip_record)

    def __recent_filter(self, before_not_after : Optional[ bool ] = True) -> Dict[ str, Any ]:

        # obtain current time
        current_time = TimeStamp.current_time()

        # specify whether new or old records
        comparison_function = ((lambda a, b : a <= b) 
            if (before_not_after) else (lambda a, b : a >= b)
        )

        def verify_recent(document : Dict[ str, Any ]) -> bool:

            nonlocal current_time, comparison_function

            # elapsed time since record creation
            elapsed_time = (current_time - TimeStamp.string2time(document["timestamp"])).total_seconds()
            
            # before or after backtrace period
            return comparison_function(elapsed_time, self._FAILURE_BACKTRACE_PERIOD)

        return verify_recent

    def _prune_memory(self) -> None:

        # remove records older than backtrace period
        #self.collection.delete_many(self.__recent_filter(before_not_after = False))

        old_failures = self.collection.find({ "is_failure" : True })

        deletion_ids = []

        recent_filter = self.__recent_filter(False)

        for document in old_failures:

            if (recent_filter(document)):

                deletion_ids.append(document["_id"])

        self.collection.delete_many({ "_id" : { "$in" : deletion_ids } })

    def num_failures(self, ip_address : str) -> int:

        ip_failures = self.collection.find({ "ip-address" : ip_address, "is_failure" : True })

        counter = 0

        recent_filter = self.__recent_filter()

        for document in ip_failures:
            if (recent_filter(document)):
                counter += 1

        return counter 