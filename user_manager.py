from email_manager import GmailManager
from pymongo.database import Database
from bson.objectid import ObjectId
import hashlib, random 
from typing import *

def generate_random_salt(length : int) -> str:

    # verify length variable is positive integer
    assert (isinstance(length, int) and (length > 0))

    # generate random string containing uppercase alphabets
    return "".join(chr(random.randint(65, 90)) for _ in range(length))

def hash_password_and_salt(password : str, salt : str) -> str:

    # verify password and salt are non-empty strings
    assert ((len(password) > 0) and (len(salt) > 0))

    # initialize SHA-256 hashing object
    hash_object = hashlib.sha256()

    # concatenate password with salt, encode into binary, then hash
    hash_object.update(f"{password}{salt}".encode("utf-8"))

    # obtain hexidecimal digest
    return hash_object.hexdigest()

class User(dict):

    def __init__(self, username      : str, 
                       password      : str, 
                       salt_length   : Optional[ int ] = 30) -> None:

        super(User, self).__init__()

        # generate random salt string
        random_salt = generate_random_salt(salt_length)

        # hash password and salt
        password_hash = hash_password_and_salt(password, random_salt)
        
        # initialize user document structure
        self.update({
            "username"           : username,
            "password_salt"      : random_salt,
            "password_hash"      : password_hash,
            "bookmarks"          : [],
            "recommended"        : [],
            "unread_recommended" : []
        })

class UserManager:

    # user collection name
    _USER_COLLECTION_NAME = "users"

    # salt string length
    _SALT_LENGTH = 30

    def __init__(self, database : Database, gmail_manager : GmailManager) -> None:

        # Food-Fellow (MongoDB) database object
        self.database = database 

        # used to send email notification
        self.gmail_manager = gmail_manager

        # collection containing user information
        #self.collection = self.database[self._USER_COLLECTION_NAME]
        self.collection = getattr(self.database.db, self._USER_COLLECTION_NAME)

    def add_user(self, username : str, password : str) -> None:

        # add new user to database (using default salt length)
        self.collection.insert_one(document = User(username, password, self._SALT_LENGTH))

    def user_exists(self, username : str) -> bool:

        # check if username exists in database
        return (self.collection.find_one(filter = { "username" : username }) is not None)

    def fetch_bookmarks(self, username : str) -> List[ ObjectId ]:

        # fetch review IDs bookmarked by user
        return self.collection.find_one(filter = { "username" : username })["bookmarks"]

    def bookmark_to_user(self, username : str, review_id : ObjectId) -> bool:

        # condition to find specific user
        username_filter = { "username" : username }

        # check if review already bookmarked
        bookmarked = self.bookmarked_to_user(username, review_id)

        # remove bookmark if bookmarked, add it otherwise
        bookmark_update = { (("$pull") if (bookmarked) else ("$push")) : { "bookmarks" : review_id } } 

        # commit change to database
        self.collection.update_one(filter = username_filter, update = bookmark_update)

        # return bookmark newest state
        #   1. bookmarked     => True
        #   2. not bookmarked => False
        return not bookmarked

    def recommend_to_user(self, username : str, review_id : ObjectId, recommender : str) -> bool:

        # check if review already recommended
        if (self._recommended_to_user(username, review_id)):

            # return False to indicate no changes are made
            return False 

        # commit recommendation update to database
        self.collection.update_one(
            filter = { "username" : username                             },
            update = { "$push"    : { "unread_recommended" : review_id } }
        )

        subject = "Food-Fellow: A New Recommendation"

        body = f"{recommender} has recommended a review to you!"

        self.gmail_manager.send(username, subject, body)

        # return True to indicate changes are made
        return True 

    def bookmarked_to_user(self, username : str, review_id : ObjectId) -> bool:

        # check if user bookmarked target review
        return (review_id in self.collection.find_one({ "username" : username })["bookmarks"])

    def _recommended_to_user(self, username : str, review_id : ObjectId) -> bool:

        # fetch user information
        user_document = self.collection.find_one({ "username" : username })

        # check if review has been previously recommended
        #   1. True  => recommended
        #   2. False => not recommended
        return (
            (review_id in user_document["recommended"       ]) or 
            (review_id in user_document["unread_recommended"])
        )

    def _mark_recommendations(self, username : str) -> None:

        # fetch user information
        user_document = self.collection.find_one({ "username" : username })

        # obtain unread recommendations
        unread_recommendations = user_document["unread_recommended"]

        # move recommendations from unread to read
        self.collection.update_one(
            filter = { "username" : username },
            update = { 
                "$push" : { "recommended"        : { "$each" : unread_recommendations } } ,
                "$set"  : { "unread_recommended" : []                                   }
            }
        )

    def fetch_recommendations(self, username : str, mark_read : Optional[ bool ] = True) -> List[ ObjectId ]:

        # fetch user information
        user_document = self.collection.find_one({ "username" : username })

        # join recommended reviews whether read or unread
        recommendations = (
            user_document["unread_recommended"] + 
            user_document["recommended"]
        )

        # mark recommendations as read if specified
        if (mark_read):
            self._mark_recommendations(username)

        # return recommended reviews
        return recommendations

    def recommendations_unread(self, username : str) -> bool:

        # check whether user has unread recommendations
        return (len(self.collection.find_one({ "username" : username })["unread_recommended"]) > 0)

    def fetch_password_and_salt(self, username : str) -> Tuple[ str, str ]:

        # fetch user information
        user_document = self.collection.find_one({ "username" : username })

        # return password hash and salt
        return (
            user_document["password_hash"], user_document["password_salt"]
        )

if (__name__ == "__main__"):

    pass    