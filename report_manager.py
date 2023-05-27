from review_manager import ReviewManager
from email_manager import GmailManager
from crypto_utils import CryptoUtils
from bson.objectid import ObjectId
from typing import *
import os 

class ReportManager(CryptoUtils):

    # admin's email address
    _ADMIN_EMAIL = "watersprayer127@gmail.com"#os.environ["FOOD_FELLOW_ADMIN_EMAIL"]
    
    # home page URL
    BASE_SITE_URL = "http://localhost:5000"#os.environ["FOOD_FELLOW_BASE"]

    def __init__(self, review_manager : ReviewManager, gmail_manager : GmailManager) -> None:

        super(ReportManager, self).__init__()

        # used to access reviews in database
        self.review_manager = review_manager 

        # used to send emails
        self.gmail_manager = gmail_manager 

    def __create_removal_object(self, review_id : ObjectId):

        # pack review ID into dictionary
        return {
            "review-id" : str(review_id)
        }

    def report_review(self, review_id : ObjectId, username : str) -> bool:

        # report failed if target review does not exist
        if not (self.review_manager.review_exists(review_id)):
            return False

        # email subject
        subject = "Food-Fellow Review Report"

        # pack review ID and encrypt it
        success, removal_key = self._encrypt_data(self.__create_removal_object(review_id))

        # encryption failed
        if not (success):
            return False 

        # format removal link
        #    "http://localhost:5000/remove?key=ABC"
        removal_key = os.path.join(self.BASE_SITE_URL, "remove").replace("\\", "/") + f"?key={removal_key}"

        # email content with removal link
        content = f"User: {username}\nReview: {str(review_id)}\nRemoval Link: {removal_key}"

        # send report ticket to admin's email address
        return self.gmail_manager.send(self._ADMIN_EMAIL, subject, content)

    def respond_to_report(self, removal_key : str) -> bool:

        # attempt to decrypt the message
        success, removal_obj = self._decrypt_data(removal_key)

        # decryption failure
        if not (success):
            return False 

        # extract review ID
        review_id = ObjectId(removal_obj["review-id"])

        # review has already been removed
        if not (self.review_manager.review_exists(review_id)):
            return False 

        # remove review
        self.review_manager.remove_review(review_id)

        # signal removal success
        return True 