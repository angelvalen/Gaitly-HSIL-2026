import os

from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, invalid
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQL
conn = sqlite3.connect("data/base.db")
cursor = conn.cursor()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Session

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", message="Please provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", message="Please provide password")

        # Query database for username
        rows = cursor.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return render_template("login.html", message="Wrong password or username")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        db_usernames = cursor.execute("SELECT username FROM users")

        # Ensure correct username
        if not username:
            return render_template("register.html", message="Please provide username")
        if len(username) > 10:
            return render_template("register.html", message="Username max length is 10 characters")
        for person in db_usernames:
            if person["username"] == username:
                return render_template("register.html", message="Username already taken")

        # Ensure password was submitted
        if not password or not confirmation:
            return render_template("register.html", message="Please provide password")

        # Ensure password was confrimed
        if password != confirmation:
            return render_template("register.html", message="Pasword and confirmation dont match")

        # Ensure password has 8+ letters, numbers and symbols
        if invalid(password):
            return render_template("register.html", message="Password must have 8 or more character and must contain numbers and symbols")

        cursor.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            username,
            generate_password_hash(password),
        )
        return redirect("/")
    else:
        return render_template("register.html")

# Execution

@app.route("/")
@login_required
def index():
        user = cursor.execute("SELECT username, bio, picture FROM users WHERE id = ?", session["user_id"])[0]
        albums = cursor.execute("SELECT * FROM albums WHERE user_id = ? ORDER BY date_of_creation DESC", session["user_id"])
        return render_template("index.html", user=user, albums=albums)
