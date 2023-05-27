from flask import Flask, session, request, url_for, redirect, render_template
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from flask_session import Session

from report_manager import ReportManager
from access_manager import AccessManager
from review_manager import ReviewManager, ReviewCondition, Review
from email_manager import GmailManager
from user_manager import UserManager
from ip_manager import IPManager

import json, os

app = Flask(__name__)

app.config["MONGO_URI"] = "mongodb://localhost:27017/food-fellow"#os.environ["MONGO_FOOD_FELLOW"]

app.config["SESSION_TYPE"] = "filesystem"

app.config["SECRET_KEY"] = "super-duper-secret-key"#os.environ["SESSION_SECRET_KEY"]

Session(app)

database = PyMongo(app)

review_manager = ReviewManager(database)

ip_manager = IPManager(database)

gmail_manager = GmailManager("ndhusmartank@gmail.com", "elkperuybhrkqrvt")#(os.environ["FOOD_FELLOW_USR"], os.environ["FOOD_FELLOW_PWD"])

user_manager = UserManager(database, gmail_manager)

access_manager = AccessManager(user_manager, gmail_manager, ip_manager)

report_manager = ReportManager(review_manager, gmail_manager)

def user_logged_in() -> bool:
    return (session.get("username", None) is not None)

@app.route("/")
def index():
    # ask the user to login if they have not
    if (session.get("username", None) is None):
        return render_template("login.html")
    # show the home page
    return render_template("index.html")

LOGOUT_STRING_STATES = ("not-logged-in", "logged-out")

LOGOUT_STATE_SIGN_IN = 0

LOGOUT_STATE_LOG_OUT = 1

LOGOUT_RETURN_STATUS = "status"

@app.route("/logout", methods = [ "POST", "GET" ])
def logout():

    response_message = { LOGOUT_RETURN_STATUS : LOGOUT_STRING_STATES[LOGOUT_STATE_SIGN_IN] }

    if (user_logged_in()):

        # log user out
        del session["username"]

        # user logged out
        response_message[LOGOUT_RETURN_STATUS] = LOGOUT_STRING_STATES[LOGOUT_STATE_LOG_OUT]

    if (request.method == "POST"):
        return json.dumps(response_message)

    return redirect(url_for("index"))
    
LOGIN_STRING_STATES = ("already-logged-in", "login-success", "incorrect-password", "invalid-username", "access-denied", "internal-error")

LOGIN_STATE_ALREADY = 0

LOGIN_STATE_SUCCESS = 1

LOGIN_STATE_INVALID = 2

LOGIN_STATE_NO_USER = 3

LOGIN_STATE_BLOCKED = 4

LOGIN_STATE_ANOTHER = 5

LOGIN_RETURN_STATUS = "status"

@app.route("/login", methods = [ "POST" ])
def login():

    # extract username
    username = request.get_json().get("username", "")

    # extract password
    password = request.get_json().get("password", "")

    if ((username == "") or (password == "")):
        return json.dumps({  REGISTER_RETURN_STATUS : REGISTER_STRING_STATES[REGISTER_STATE_ANOTHER]  })
        
    # obtain the IP address
    ip_address = request.remote_addr

    response_message = { LOGIN_RETURN_STATUS : LOGIN_STRING_STATES[LOGIN_STATE_ALREADY] }

    # BRANCH 0 : user already logged in
    if (user_logged_in()):
        return json.dumps(response_message)

    # authenticate user credentials
    login_status = access_manager.authenticate_login(username, password, ip_address)

    # BRANCH 1 : successful login
    if (login_status == access_manager.STATE_LOGIN_SUCCESS):

        response_message[LOGIN_RETURN_STATUS] = LOGIN_STRING_STATES[LOGIN_STATE_SUCCESS]

        # log user in
        session["username"] = username 

    # BRANCH 2 : incorrect password
    elif (login_status == access_manager.STATE_LOGIN_INVALID):
        response_message[LOGIN_RETURN_STATUS] = LOGIN_STRING_STATES[LOGIN_STATE_INVALID]

    # BRANCH 3 : invalid username
    elif (login_status == access_manager.STATE_LOGIN_NO_USER):
        response_message[LOGIN_RETURN_STATUS] = LOGIN_STRING_STATES[LOGIN_STATE_NO_USER]

    # BRANCH 5 : IP blocked due to excessive attempts
    elif (login_status == access_manager.STATE_LOGIN_BLOCKED):
        response_message[LOGIN_RETURN_STATUS] = LOGIN_STRING_STATES[LOGIN_STATE_BLOCKED]

    # BRANCH 5 : unexpected errors (for debugging)
    else:
        response_message[LOGIN_RETURN_STATUS] = LOGIN_STRING_STATES[LOGIN_STATE_ANOTHER]

    return json.dumps(response_message)

REGISTER_STRING_STATES = ("already-logged-in", "register-success", "already-registered", "register-failure", "internal-error")

REGISTER_STATE_SIGN_IN = 0

REGISTER_STATE_SUCCESS = 1

REGISTER_STATE_ALREADY = 2

REGISTER_STATE_FAILURE = 3

REGISTER_STATE_ANOTHER = 4

REGISTER_RETURN_STATUS = "status"

@app.route("/register", methods = [ "POST" ])
def register():

    # extract username
    username = request.get_json().get("username", "")

    # extract password
    password = request.get_json().get("password", "")

    if ((username == "") or (password == "")):
        return json.dumps({  REGISTER_RETURN_STATUS : REGISTER_STRING_STATES[REGISTER_STATE_ANOTHER]  })

    response_message = {  REGISTER_RETURN_STATUS : REGISTER_STRING_STATES[REGISTER_STATE_SIGN_IN]  }

    # BRANCH 0 : user already logged in
    if (user_logged_in()):
        return json.dumps(response_message)
    
    # register account
    register_status = access_manager.register_account(username, password)

    # BRANCH 1 : registration success
    if (register_status == access_manager.STATE_REGISTER_SUCCESS):
        response_message[REGISTER_RETURN_STATUS] = REGISTER_STRING_STATES[REGISTER_STATE_SUCCESS]

    # BRANCH 2 : account has already been registered
    elif (register_status == access_manager.STATE_REGISTER_ALREADY):
        response_message[REGISTER_RETURN_STATUS] = REGISTER_STRING_STATES[REGISTER_STATE_ALREADY]

    # BRANCH 3 : registration failure 
    elif (register_status == access_manager.STATE_REGISTER_FAILURE):
        response_message[REGISTER_RETURN_STATUS] = REGISTER_STRING_STATES[REGISTER_STATE_FAILURE]

    # BRANCH 4 : unexpected error (for debugging)
    else:
        response_message[REGISTER_RETURN_STATUS] = REGISTER_STRING_STATES[REGISTER_STATE_ANOTHER]

    return json.dumps(response_message)

ACTIVATE_STRING_STATES = ("already-activated", "activation-success", "activation-failure", "internal-error")

ACTIVATE_STATE_ALREADY = 0

ACTIVATE_STATE_SUCCESS = 1

ACTIVATE_STATE_FAILURE = 2

ACTIVATE_STATE_ANOTHER = 3

ACTIVATE_RETURN_STATUS = "status"

@app.route("/activate", methods = [ "GET" ])
def activate():

    # fetch activation key from argument
    activation_key = request.args.get("key", None)

    response_message = { ACTIVATE_RETURN_STATUS : ACTIVATE_STRING_STATES[ACTIVATE_STATE_ANOTHER] }

    # BRANCH 3 : no activation key is found
    if (activation_key is None):
        return json.dumps(response_message)

    activate_status = access_manager.activate_account(activation_key)

    # BRANCH 0 : account already activated
    if (activate_status == access_manager.STATE_ACTIVATE_ALREADY):
        response_message[ACTIVATE_RETURN_STATUS] = ACTIVATE_STRING_STATES[ACTIVATE_STATE_ALREADY]

    # BRANCH 1 : account successfully activated
    elif (activate_status == access_manager.STATE_ACTIVATE_SUCCESS):
        response_message[ACTIVATE_RETURN_STATUS] = ACTIVATE_STRING_STATES[ACTIVATE_STATE_SUCCESS]

    # BRANCH 2 : activation failure
    elif (activate_status == access_manager.STATE_ACTIVATE_FAILURE):
        response_message[ACTIVATE_RETURN_STATUS] = ACTIVATE_STRING_STATES[ACTIVATE_STATE_FAILURE]

    return json.dumps(response_message)

UPVOTE_STRING_STATES = ("internal-error", "review-not-found", "not-logged-in", "upvote-success")

UPVOTE_STATE_ANOTHER = 0

UPVOTE_STATE_NOEXIST = 1

UPVOTE_STATE_SIGN_IN = 2

UPVOTE_STATE_SUCCESS = 3

UPVOTE_RETURN_STATUS = "status"

@app.route("/upvote", methods = [ "POST" ])
def upvote():

    # BRANCH 2 : user not logged in
    if not (user_logged_in()):
        return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_SIGN_IN] })
    
    # fetch review ID
    review_id = request.json.get("review-id", None)

    # fetch username
    username = session.get("username", None)

    # BRANCH 0 : review ID not provided
    if ((review_id is None) or (username is None)):
        return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_ANOTHER] })
    
    # convert review ID to ObjectId
    review_id = ObjectId(review_id)

    # BRANCH 1 : target review does not exist
    if not (review_manager.review_exists(review_id)):
        return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_NOEXIST] })
    
    # toggle upvote status
    upvote_state = review_manager.upvote_review(username, review_id)

    # BRANCH 3 : upvote (toggle) successful
    return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_SUCCESS], "upvote-state" : upvote_state })

BOOKMARK_STRING_STATES = ("internal-error", "not-logged-in", "bookmark-success")

BOOKMARK_STATE_ANOTHER = 0

BOOKMARK_STATE_SIGN_IN = 1

BOOKMARK_STATE_SUCCESS = 2

BOOKMARK_RETURN_STATUS = "status"

@app.route("/bookmark", methods = [ "POST" ])
def bookmark():

    # BRANCH 1 : user has not logged in
    if not (user_logged_in()):
        return json.dumps({ BOOKMARK_RETURN_STATUS : BOOKMARK_STRING_STATES[BOOKMARK_STATE_SIGN_IN] })

    # fetch review ID
    review_id = request.json.get("review-id", "")

    # fetch username
    username = session.get("username", "")

    # BRANCH 0 : user not logged in or review not specified
    if ((review_id == "") or (username == "")):
        return json.dumps({ BOOKMARK_RETURN_STATUS : BOOKMARK_STRING_STATES[BOOKMARK_STATE_ANOTHER] })

    # bookmark review to user
    bookmark_state = user_manager.bookmark_to_user(username, ObjectId(review_id))

    # BRANCH 2 : bookmark successful
    return json.dumps({ BOOKMARK_RETURN_STATUS : BOOKMARK_STRING_STATES[BOOKMARK_STATE_SUCCESS], "bookmark-state" : bookmark_state })

RECOMMEND_STRING_STATES = ("not-logged-in", "internal-error", "recommend-success", "invalid-user")

RECOMMEND_STATE_SIGN_IN = 0

RECOMMEND_STATE_ANOTHER = 1

RECOMMEND_STATE_SUCCESS = 2

RECOMMEND_STATE_NO_USER = 3

RECOMMEND_RETURN_STATUS = "status"

@app.route("/recommend", methods = [ "POST" ])
def recommend():

    # BRANCH 0 : user has not logged in
    if not (user_logged_in()):
        return json.dumps({ RECOMMEND_RETURN_STATUS : RECOMMEND_STRING_STATES[RECOMMEND_STATE_SIGN_IN] })

    # fetch recommender username
    recommender = session.get("username", "")

    # fetch receiver username
    username = request.json.get("username", "")

    # fetch review ID
    review_id = request.json.get("review-id", "")

    # BRANCH 1 : any field not specified
    if ((recommender == "") or (username == "") or (review_id == "")):
        return json.dumps({ RECOMMEND_RETURN_STATUS : RECOMMEND_STRING_STATES[RECOMMEND_STATE_ANOTHER] })

    # convert review ID to ObjectId
    review_id = ObjectId(review_id)

    # BRANCH 3 : specified user does not exist
    if not (user_manager.user_exists(username)):
        return json.dumps({ RECOMMEND_RETURN_STATUS : RECOMMEND_STRING_STATES[RECOMMEND_STATE_NO_USER]})

    # recommend to user
    recommend_state = user_manager.recommend_to_user(username, review_id, recommender)

    # BRANCH 2 : recommendation successful
    return json.dumps({ RECOMMEND_RETURN_STATUS : RECOMMEND_STRING_STATES[RECOMMEND_STATE_SUCCESS], "recommend-state" : recommend_state })

REPORT_STRING_STATES = ("not-logged-in", "internal-error", "report-failure", "report-success")

REPORT_STATE_SIGN_IN = 0

REPORT_STATE_ANOTHER = 1

REPORT_STATE_FAILURE = 2

REPORT_STATE_SUCCESS = 3

REPORT_RETURN_STATUS = "status"

@app.route("/report", methods = [ "POST" ])
def report():

    # BRANCH 0 : user not logged in
    if not (user_logged_in()):
        return json.dumps({
            REPORT_RETURN_STATUS : REPORT_STRING_STATES[REPORT_STATE_SIGN_IN]
        })
    
    # fetch username
    username = session.get("username", "")

    # fetch review ID
    review_id = request.get_json().get("review-id", "")

    # BRANCH 1 : username or review ID unspecified
    if ((username == "") or (review_id == "")):
        return json.dumps({
            REPORT_RETURN_STATUS : REPORT_STRING_STATES[REPORT_STATE_ANOTHER]
        })

    # send report ticket to admin
    report_status = report_manager.report_review(review_id, username)

    # BRANCH 3 : report successful
    if (report_status):
        return json.dumps({
            REPORT_RETURN_STATUS : REPORT_STRING_STATES[REPORT_STATE_SUCCESS]
        })

    # BRANCH 2 : report failure
    return json.dumps({
        REPORT_RETURN_STATUS : REPORT_STRING_STATES[REPORT_STATE_FAILURE]
    })

REMOVAL_STRING_STATES = ("internal-error", "removal-success", "removal-failure")

REMOVAL_STATE_ANOTHER = 0

REMOVAL_STATE_SUCCESS = 1

REMOVAL_STATE_FAILURE = 2

REMOVAL_RETURN_STATUS = "status"

@app.route("/remove", methods = [ "GET" ])
def remove():

    # extract removal key
    removal_key = request.args.get("key", "")

    # BRANCH 0 : removal key empty
    if (removal_key == ""):
        return json.dumps({
            REMOVAL_RETURN_STATUS : REMOVAL_STRING_STATES[REMOVAL_STATE_ANOTHER]
        })

    # attempt to remove review
    removal_status = report_manager.respond_to_report(removal_key)

    # BRANCH 1 : review removal was successful
    if (removal_status):
        return json.dumps({
            REMOVAL_RETURN_STATUS : REMOVAL_STRING_STATES[REMOVAL_STATE_SUCCESS]
        })

    # BRANCH 2 : review removal failed
    return json.dumps({
        REMOVAL_RETURN_STATUS : REMOVAL_STRING_STATES[REMOVAL_STATE_FAILURE]
    })

WRITE_STRING_STATES = ("not-logged-in", "fields-unspecified", "write-success")

WRITE_STATE_SIGN_IN = 0

WRITE_STATE_FILL_IN = 1

WRITE_STATE_SUCCESS = 2

WRITE_RETURN_STATUS = "status"

@app.route("/write", methods = [ "GET", "POST" ])
def write():

    if (request.method == "GET"):

        if not (user_logged_in()):
            return redirect(url_for("index"))

        return render_template("review.html")

    # BRANCH 0 : user not logged in
    if not (user_logged_in()):
        return json.dumps({
            WRITE_RETURN_STATUS : WRITE_STRING_STATES[WRITE_STATE_SIGN_IN]
        })

    # extract username
    author_name = session.get("username", "")

    # extract food name
    food_name = request.get_json().get("food-name", "")

    # extract restaurant name
    restaurant_name = request.get_json().get("restaurant-name", "")

    # extract food price
    food_price = request.get_json().get("food-price", "")

    # extract food rating
    food_rating = request.get_json().get("food-rating", "")

    # extract service rating
    service_rating = request.get_json().get("service-rating", "")

    # extract recommendation rating
    recommend_rating = request.get_json().get("recommend-rating", "")

    # extract hashtags
    hashtags = request.get_json().get("hashtags", [])

    hashtags = list(filter("".__ne__, hashtags))

    # BRANCH 1 : some fields were unspecified (empty)
    if any([
        author_name == "", food_name == "", restaurant_name == "", food_price == "",
        food_rating == "", service_rating == "", recommend_rating == ""
    ]):
        return json.dumps({ WRITE_RETURN_STATUS : WRITE_STRING_STATES[WRITE_STATE_FILL_IN] })

    if not all([
        food_price.isnumeric(), food_rating.isnumeric(), 
        service_rating.isnumeric(), recommend_rating.isnumeric()
    ]):
        return json.dumps({ WRITE_RETURN_STATUS : WRITE_STRING_STATES[WRITE_STATE_FILL_IN] })

    def bound_range(value):
        return min(5, max(1, value))

    # attempt to add review
    review_manager.add_review(Review(
        food_name, restaurant_name, 
        author_name, abs(int(food_price)), bound_range(int(food_rating)), 
        bound_range(int(service_rating)), bound_range(int(recommend_rating)), hashtags)
    )

    # BRANCH 2 : review successfully added
    return json.dumps({ WRITE_RETURN_STATUS : WRITE_STRING_STATES[WRITE_STATE_SUCCESS] })

@app.route("/bookmarked", methods = [ "POST" ])
def bookmarked():

    if not (user_logged_in()):
        return json.dumps({
            "status" : "not-logged-in"
        })

    username = session.get("username")

    bookmarked_ids = user_manager.fetch_bookmarks(username)

    bookmarked_reviews = review_manager.fetch_reviews_by_ids(bookmarked_ids)

    return json.dumps({
        "status" : "retrieve-success", "data" : bookmarked_reviews
    })

@app.route("/written", methods = [ "POST" ])
def written():

    if not (user_logged_in()):
        return json.dumps({
            "status" : "not-logged-in"
        })

    username = session.get("username")

    written_reviews = review_manager.fetch_reviews(ReviewCondition(author_name = username))

    return json.dumps({
        "status" : "retrieve-success", "data" : written_reviews
    })

@app.route("/recommended", methods = [ "POST" ])
def recommended():

    if not (user_logged_in()):
        return json.dumps({
            "status" : "not-logged-in"
        })

    username = session.get("username")

    recommended_ids = user_manager.fetch_recommendations(username)

    recommended_reviews = review_manager.fetch_reviews_by_ids(recommended_ids)

    return json.dumps({
        "status" : "retrieve-success", "data" : recommended_reviews
    })

@app.route("/search", methods = [ "POST" ])
def search():
    if not (user_logged_in()):
        return json.dumps({
            "status" : "user-not-logged-in"
        })
    
    search_string = request.get_json().get("search-string", "")

    if (search_string == ""):
        return json.dumps({
            "status" : "empty-search-string"
        })

    found_reviews = review_manager._advanced_query(
        { "$or" : [ { "author_name" : search_string }, { "food_name" : search_string }, { "restaurant_name" : search_string } ] }
    )

    return json.dumps({
        "status" : "retrieve-success", "data" : found_reviews
    })

if (__name__ == "__main__"):

    app.run(debug = True)