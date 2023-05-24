from flask import Flask, session, request, redirect, render_template
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from flask_session import Session

from access_manager import AccessManager
from review_manager import ReviewManager
from email_manager import GmailManager
from user_manager import UserManager
from ip_manager import IPManager

import json

app = Flask(__name__)

app.config["MONGO_URI"] = "mongodb://localhost:27017/food-fellow"

app.config["SESSION_TYPE"] = "filesystem"

app.config["SECRET_KEY"] = "super-duper-secret-key"

Session(app)

database = PyMongo(app)

user_manager = UserManager(database)

review_manager = ReviewManager(database)

ip_manager = IPManager(database)

gmail_manager = GmailManager("ndhusmartank@gmail.com", "elkperuybhrkqrvt")

access_manager = AccessManager(user_manager, gmail_manager, ip_manager)

def user_logged_in() -> bool:
    return (session.get("username", None) is not None)

@app.route("/")
def index():
    # ask the user to login if they have not
    if (session.get("username", None) is None):
        ip_address = request.remote_addr
        print("IP: {}".format(ip_address))
        print(ip_manager.ip_blacklisted(ip_address))
        return "Hello"
    # show the home page
    pass 

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

    return json.dumps(response_message)
    
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
    username = request.form.get("username", None)

    # extract password
    password = request.form.get("password", None)

    if ((username is None) or (password is None)):
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
    username = request.form.get("username", None)

    # extract password
    password = request.form.get("password", None)

    if ((username is None) or (password is None)):
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

    # BRANCH 0 : review ID not provided
    if (review_id is None):
        return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_ANOTHER] })
    
    # convert review ID to ObjectId
    review_id = ObjectId(review_id)

    # BRANCH 1 : target review does not exist
    if not (review_manager.review_exists(review_id)):
        return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_NOEXIST] })
    
    # toggle upvote status
    upvote_state = review_manager.upvote_review(session.get("username"), review_id)

    # BRANCH 3 : upvote (toggle) successful
    return json.dumps({ UPVOTE_RETURN_STATUS : UPVOTE_STRING_STATES[UPVOTE_STATE_SUCCESS], "upvote-state" : upvote_state })

@app.route("/search", methods = [ "POST" ])
def search():
    if not (user_logged_in()):
        return json.dumps({
            "status" : "user-not-logged-in"
        })

if (__name__ == "__main__"):

    app.run(debug = True)