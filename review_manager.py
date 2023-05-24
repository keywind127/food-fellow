from datetime import datetime, timezone
from pymongo.database import Database
from bson.objectid import ObjectId
from typing import *

class ReviewCondition(dict):

    _STRICT_MATCHING = { 
        "food_name", "restaurant_name", "author_name", "food_rating", 
        "service_rating", "recommend_rating" 
    }

    _RANGE_MATCHING = {
        "food_price_range"
    }

    _ITEM_MATCHING = {
        "hashtags"
    }

    def __init__(self, food_name        : Optional[ str               ] = None,
                       restaurant_name  : Optional[ str               ] = None,
                       author_name      : Optional[ str               ] = None,
                       food_price_range : Optional[ Tuple[ int, int ] ] = None,
                       food_rating      : Optional[ int               ] = None,
                       service_rating   : Optional[ int               ] = None,
                       recommend_rating : Optional[ int               ] = None,
                       hashtags         : Optional[ List[ str ]       ] = None) -> None:

        super(ReviewCondition, self).__init__()

        self.update({
            "food_name"        : food_name,
            "restaurant_name"  : restaurant_name,
            "author_name"      : author_name,
            "food_price_range" : food_price_range,
            "food_rating"      : food_rating,
            "service_rating"   : service_rating,
            "recommend_rating" : recommend_rating,
            "hashtags"         : hashtags
        })

class Review(dict):

    _TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

    _HIDDEN_FIELDS = {  "upvoters", "timestamp"  }

    def __init__(self, food_name        : str,
                       restaurant_name  : str,
                       author_name      : str,
                       food_price       : int,
                       food_rating      : int,
                       service_rating   : int,
                       recommend_rating : int,
                       hashtags         : Optional[ List[ str ] ] = []) -> None:
        
        super(Review, self).__init__()

        self.update({
            "food_name"        : food_name,
            "restaurant_name"  : restaurant_name,
            "author_name"      : author_name,
            "food_price"       : food_price,
            "food_rating"      : food_rating,
            "service_rating"   : service_rating,
            "recommend_rating" : recommend_rating,
            "upvoters"         : [],
            "num_upvotes"      : 0,
            "hashtags"         : hashtags,
            "timestamp"        : datetime.now(timezone.utc).strftime(self._TIMESTAMP_FORMAT)
        })

    @classmethod
    def simplify(self, review_document : Dict[ str, Any ]) -> Dict[ str, Any ]:
        return {
            key : value for key, value in review_document.items()
                if key not in class_._HIDDEN_FIELDS
        }

class ReviewManager:

    # review collection name
    _REVIEW_COLLECTION_NAME = "reviews"

    def __init__(self, database : Database) -> None:

        # Food-Fellow (MongoDB) database object
        self.database = database 

        # collection containing review information
        #self.collection = self.database[self._REVIEW_COLLECTION_NAME]
        self.collection = getattr(self.database.db, self._REVIEW_COLLECTION_NAME)

    def add_review(self, review : Review) -> None:

        # verify review has been correctly formatted
        assert isinstance(review, Review)

        # add review to database
        self.collection.insert_one(document = review)

    def remove_review(self, review_id : ObjectId) -> None:

        # only remove existing reviews
        if (self.review_exists(review_id)):

            # remove review according to specified ID
            self.collection.delete_one(filter = { "_id" : review_id })

    def upvote_review(self, username : str, review_id : ObjectId) -> bool:

        # check if user has already upvoted target review
        upvoted = self.review_upvoted(username, review_id)

        # condition to find specific review (by IDs)
        review_filter = { "_id" : review_id }

        # remove upvote if upvoted, add it otherwise
        upvote_update = { (("$pull") if (upvoted) else ("$push")) : { "upvoters" : username } }

        # decrement counter if upvoted, increment it otherwise
        upvote_update.update({ "$inc" : { "num_upvotes" : ((-1) if (upvoted) else (1)) } })

        # commit changes to database
        self.collection.update_one(filter = review_filter, update = upvote_update)

        # return (newest) upvote status
        #   1. True  => upvoted
        #   2. False => not upvoted
        return not upvoted

    def review_upvoted(self, username : str, review_id : ObjectId) -> bool:

        # fetch review information
        review_information = self.collection.find_one(filter = { "_id" : review_id })

        # check if user has upvoted target review
        return (username in review_information["upvoters"])

    def review_exists(self, review_id : ObjectId) -> bool:

        # check if review exists in database
        return (self.collection.find_one(filter = { "_id" : review_id }) is not None)

    def fetch_reviews_by_ids(self, id_list : List[ ObjectId ]) -> List[ Dict[ str, Any ] ]:

        # find reviews with matching ID, and remove sensitive attributes with "simplify" method
        return list(map(Review.simplify, self.collection.find({ "_id" : { "$in" : id_list } })))

    def fetch_reviews(self, review_filter : ReviewCondition) -> List[ Dict[ str, Any ] ]:

        assert isinstance(review_filter, ReviewCondition)

        # instantiate query conditions
        filter_conditions = dict()

        for attribute_name, attribute_value in review_filter.items():

            # skip if argument unspecified
            if (attribute_value is None):
                continue 

            # "strict matching" uses direct comparison
            if (attribute_name in review_filter._STRICT_MATCHING):

                # e.q. { "field" : "value" }
                query_rule = attribute_value 

            # "range matching" uses boundary comparison
            elif (attribute_name in review_filter._RANGE_MATCHING):

                # e.q. { "field" : { "$gte" : lower_value, "$lte" : upper_value } }
                query_rule = {
                    "$gte" : attribute_value[0],
                    "$lte" : attribute_value[1]
                }

            # item matching checks if everything in target list is included
            elif (attribute_name in review_filter._ITEM_MATCHING):

                # e.q. { "field" : { "$all" : [ value_1, value_2 ] } }
                query_rule = {
                    "$all" : list(attribute_value)
                }

            else:

                # raise an exception on unexpected attribute name
                raise Exception(f"Invalid field name for review searching: {repr(attribute_name)}\n")

            # apply the rule
            filter_conditions[attribute_name] = query_rule

        # find reviews satisfying the criteria, and remove sensitive attributes with "simplify" method
        return list(map(Review.simplify, self.collection.find(filter_conditions)))

if (__name__ == "__main__"):

    pass    