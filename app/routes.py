from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, Word, Game
from datetime import datetime, date, timedelta
from sqlalchemy import cast, Date
from functools import wraps
import random
import re
from sqlalchemy import func, case

main = Blueprint("main", __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# Home Route
@main.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


# Updated Registration Route
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Instead of redirecting, we re-render the template with the submitted data
        if len(username) < 5:
            flash("Username must be at least 5 characters long.", "danger")
            return render_template("register.html", username=username, email=email)
        
        if not (re.search('[a-z]', username) and re.search('[A-Z]', username)):
            flash("Username must contain both uppercase and lowercase letters.", "danger")
            return render_template("register.html", username=username, email=email)
        
        if len(password) < 5:
            flash("Password must be at least 5 characters long.", "danger")
            return render_template("register.html", username=username, email=email)
        
        if not (re.search('[a-zA-Z]', password) and re.search('[0-9]', password) and re.search('[$%*@]', password)):
            flash("Password must contain a letter, a number, and one of these special characters: $, %, *, @", "danger")
            return render_template("register.html", username=username, email=email)
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please try a different one or log in.", "danger")
            return render_template("register.html", username=username, email=email)
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.", "danger")
            return render_template("register.html", username=username, email=email)
        
        if User.query.first() is None:
            new_user = User(username=username, email=email, is_admin=True)
            flash("Congratulations! As the first user, you have been made an admin.", "info")
            sample_words = [
                "APPLE", "BRAIN", "CHAIR", "DELTA", "EAGLE", "FAITH", "GIANT", 
                "HOUSE", "INPUT", "JOKER", "KNIFE", "LIGHT", "MONEY", "NURSE", 
                "OCEAN", "PLANT", "QUEEN", "ROBOT", "SUGAR", "TIGER"
            ]
            for w in sample_words:
                db.session.add(Word(word=w))
            flash("Initial word list has been populated automatically.", "success")
        else:
            new_user = User(username=username, email=email, is_admin=False)

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
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    return render_template("login.html")

@main.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))

@main.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("main.login"))
    return render_template("dashboard.html", username=session.get("username"))

@main.route("/play", methods=["GET", "POST"])
def play():
    if "user_id" not in session:
        flash("Please log in to play.", "warning")
        return redirect(url_for("main.login"))

    if "target_word" not in session:
        today = datetime.utcnow().date()
        games_today = Game.query.filter(
            Game.user_id == session['user_id'],
            cast(Game.played_at, Date) == today
        ).count()

        if games_today >= 3:
            flash("You have already played your 3 games for today. Please come back tomorrow!", "warning")
            return redirect(url_for('main.dashboard'))

        words = Word.query.all()
        if not words:
            flash("Error: No words found in the database.", "danger")
            return redirect(url_for("main.dashboard"))
        target_word = random.choice(words).word.upper()
        session["target_word"] = target_word
        session["attempts"] = 0
        session["history"] = []

    history = session.get("history", [])
    target = session.get("target_word")
    game_over = False
    message = None

    if request.method == "POST":
        guess = request.form.get("guess", "").strip().upper()

        if not guess.isalpha() or len(guess) != 5:
            flash("Invalid input. Please enter a single 5-letter word.", "danger")
            return redirect(url_for("main.play"))
            
        previous_guesses = ["".join([letter['letter'] for letter in attempt]) for attempt in history]
        if guess in previous_guesses:
            flash(f"You've already guessed the word '{guess}'. Try a different one!", "warning")
            return redirect(url_for("main.play"))

        session["attempts"] += 1

        feedback = []
        target_counts = {char: target.count(char) for char in set(target)}
        for i in range(5):
            if guess[i] == target[i]:
                feedback.append({"letter": guess[i], "color": "green"})
                target_counts[guess[i]] -= 1
            else:
                feedback.append({"letter": guess[i], "color": "grey"})
        for i in range(5):
            if feedback[i]['color'] != 'green':
                if guess[i] in target and target_counts.get(guess[i], 0) > 0:
                    feedback[i]['color'] = 'orange'
                    target_counts[guess[i]] -= 1
        
        history.append(feedback)
        session["history"] = history

        if guess == target:
            game_over = True
            message = f"CONGRATULATIONS! You guessed '{target}' in {session['attempts']} attempts!"
            new_game = Game(user_id=session["user_id"], word=target, attempts=session["attempts"], won=True, played_at=datetime.utcnow())
            db.session.add(new_game)
        
        elif session["attempts"] >= 5:
            game_over = True
            message = f"GAME OVER! The word was '{target}'."
            new_game = Game(user_id=session["user_id"], word=target, attempts=session["attempts"], won=False, played_at=datetime.utcnow())
            db.session.add(new_game)
        
        if game_over:
            db.session.commit()
            session.pop("target_word", None)
            session.pop("attempts", None)
            session.pop("history", None)

    return render_template(
        "play.html",
        history=history,
        game_over=game_over,
        message=message,
        attempts=session.get('attempts', 0)
    )

@main.route("/leaderboard")
def leaderboard():
    if "user_id" not in session:
        flash("Please log in to view the leaderboard.", "warning")
        return redirect(url_for("main.login"))
    stats = (
        db.session.query(
            User.username,
            func.count(Game.id).label("games_played"),
            func.sum(case((Game.won == True, 1), else_=0)).label("wins")
        )
        .join(Game, Game.user_id == User.id)
        .group_by(User.id)
        .order_by(
            func.sum(case((Game.won == True, 1), else_=0)).desc(),
            func.count(Game.id).asc()
        ).all()
    )
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

# Admin Dashboard Route
@main.route("/admin", methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    today = datetime.utcnow().date()
    total_users = User.query.count()
    games_today = Game.query.filter(cast(Game.played_at, Date) == today).count()
    wins_today = Game.query.filter(cast(Game.played_at, Date) == today, Game.won == True).count()
    search_term = request.form.get('username', '')
    if search_term:
        all_users = User.query.filter(User.username.ilike(f'%{search_term}%')).order_by(User.created_at.desc()).all()
    else:
        all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        games_today=games_today,
        wins_today=wins_today,
        all_users=all_users
    )

@main.route("/admin/chart-data")
@admin_required
def chart_data():
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        chart_labels.append(day.strftime("%b %d"))
        games_on_day = Game.query.filter(cast(Game.played_at, Date) == day).count()
        chart_data.append(games_on_day)
    return jsonify({'labels': chart_labels, 'data': chart_data})

@main.route("/admin/toggle-admin/<int:user_id>", methods=['POST'])
@admin_required
def toggle_admin(user_id):
    if user_id == session['user_id']:
        flash("You cannot change your own admin status.", "danger")
        return redirect(url_for('main.admin_dashboard'))
    user = User.query.get(user_id)
    if user:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f"User '{user.username}' status has been updated.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for('main.admin_dashboard'))