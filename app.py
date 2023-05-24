from flask import Flask, session, request, redirect, render_template
from flask_pymongo import PyMongo
from flask_session import Session

from access_manager import AccessManager
from review_manager import ReviewManager
from email_manager import GmailManager
from user_manager import UserManager
from ip_manager import IPManager

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

if (__name__ == "__main__"):

    app.run(debug = True)