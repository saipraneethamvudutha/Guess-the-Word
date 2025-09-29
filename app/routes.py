from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User, Word, Guess, Game
from datetime import datetime
import random
import re
from sqlalchemy import func, case

main = Blueprint("main", __name__)

# Home Route
@main.route("/")
def home():
    return render_template("home.html")


# Registration Route
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        # validations
        if len(username) < 5:
            flash("Username must be at least 5 characters long.", "danger")
            return redirect(url_for("main.register"))

        if not (re.search('[a-z]', username) and re.search('[A-Z]', username)):
            flash("Username must contain both uppercase and lowercase letters.", "danger")
            return redirect(url_for("main.register"))

        if len(password) < 5:
            flash("Password must be at least 5 characters long.", "danger")
            return redirect(url_for("main.register"))

        if not (re.search('[a-zA-Z]', password) and re.search('[0-9]', password) and re.search('[$%*@]', password)):
            flash("Password must contain a letter, a number, and one of these special characters: $, %, *, @", "danger")
            return redirect(url_for("main.register"))

        # Check existing user
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("main.login"))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# Login Route
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html")


# Logout Route
@main.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


# Dashboard Route
@main.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("main.login"))

    return render_template("dashboard.html", username=session.get("username"))


# The Main Game Logic
@main.route("/play", methods=["GET", "POST"])
def play():
    if "user_id" not in session:
        flash("Please log in to play.", "warning")
        return redirect(url_for("main.login"))

    if "target_word" not in session:
        words = Word.query.all()
        if not words:
            flash("No words available. Please add words first.", "danger")
            return redirect(url_for("main.dashboard"))
        target_word = random.choice(words).word.upper()
        session["target_word"] = target_word
        session["attempts"] = 0
        session["history"] = []

    history = session["history"]
    target = session["target_word"]
    game_over = False
    message = None

    if request.method == "POST" and not game_over:
        guess = request.form.get("guess", "").upper().strip()

        if len(guess) != 5 or not guess.isalpha():
            flash("Invalid guess. Please enter a 5-letter word.", "danger")
            return redirect(url_for("main.play"))

        session["attempts"] += 1

        feedback = []
        for i in range(5):
            if guess[i] == target[i]:
                feedback.append({"letter": guess[i], "color": "green"})
            elif guess[i] in target:
                feedback.append({"letter": guess[i], "color": "orange"})
            else:
                feedback.append({"letter": guess[i], "color": "grey"})

        history.append(feedback)
        session["history"] = history

        # Win Condition
        if guess == target:
            game_over = True
            message = f" CONGRATULATIONS ! You guessed the word '{target}' in {session['attempts']} attempts!"
            new_game = Game(
                user_id=session["user_id"],
                word=target,
                attempts=session["attempts"],
                won=True,
                played_at=datetime.utcnow()
            )
            db.session.add(new_game)
            db.session.commit()
            session.pop("target_word", None)
            session.pop("attempts", None)
            session.pop("history", None)

        # Lose Condition
        elif session["attempts"] >= 6:
            game_over = True
            message = f" GAME OVER ! The word was '{target}'."
            new_game = Game(
                user_id=session["user_id"],
                word=target,
                attempts=session["attempts"],
                won=False,
                played_at=datetime.utcnow()
            )
            db.session.add(new_game)
            db.session.commit()
            session.pop("target_word", None)
            session.pop("attempts", None)
            session.pop("history", None)

    return render_template(
        "play.html",
        history=history,
        game_over=game_over,
        message=message
    )


# Add Sample Words
@main.route("/add-words")
def add_words():
    sample_words = [
        "APPLE", "BRAIN", "CHAIR", "DELTA", "EAGLE",
        "FAITH", "GIANT", "HOUSE", "INPUT", "JOKER",
        "KNIFE", "LIGHT", "MONEY", "NURSE", "OCEAN",
        "PLANT", "QUEEN", "ROBOT", "SUGAR", "TIGER"
    ]

    for w in sample_words:
        if not Word.query.filter_by(word=w).first():
            new_word = Word(word=w)
            db.session.add(new_word)

    db.session.commit()
    return "20 words added successfully!"


@main.route("/leaderboard")
def leaderboard():
    if "user_id" not in session:
        flash("Please log in to view the leaderboard.", "warning")
        return redirect(url_for("main.login"))

    # Leaderboard Data
    stats = (
        db.session.query(
            User.username,
            func.count(Game.id).label("games_played"),
            func.sum(case((Game.won == True, 1), else_=0)).label("wins"),
            func.avg(Game.attempts).label("avg_attempts")
        )
        .join(Game, Game.user_id == User.id)
        .group_by(User.id)
        .order_by(func.sum(case((Game.won == True, 1), else_=0)).desc())
        .all()
    )

    # Personal Stats
    user_games = Game.query.filter_by(user_id=session["user_id"]).all()
    total_games = len(user_games)
    wins = sum(1 for g in user_games if g.won)
    losses = total_games - wins
    win_rate = round((wins / total_games) * 100, 2) if total_games > 0 else 0

    return render_template(
        "leaderboard.html",
        leaderboard=stats,
        total_games=total_games,
        wins=wins,
        losses=losses,
        win_rate=win_rate
    )
