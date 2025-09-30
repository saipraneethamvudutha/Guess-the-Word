from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, Word, Game, Guess
from datetime import datetime, date, timedelta, time 
from sqlalchemy import cast, Date, distinct
from functools import wraps
import random
import re
from sqlalchemy import func, case

main = Blueprint("main", __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('main.login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Home Routes
@main.route("/")
def home():
    if "user_id" in session: return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

# User Routes
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, email, password = request.form.get("username", "").strip(), request.form.get("email", "").strip(), request.form.get("password", "")
        if len(username) < 5 or not (re.search('[a-z]', username) and re.search('[A-Z]', username)):
            flash("Username must be at least 5 characters and contain both uppercase and lowercase letters.", "danger")
            return render_template("register.html", username=username, email=email)
        if len(password) < 5 or not (re.search('[a-zA-Z]', password) and re.search('[0-9]', password) and re.search('[$%*@]', password)):
            flash("Password must be at least 5 characters and include a letter, number, and special character ($, %, *, @).", "danger")
            return render_template("register.html", username=username, email=email)
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("register.html", username=username, email=email)
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template("register.html", username=username, email=email)
        
        is_first_user = User.query.first() is None
        new_user = User(username=username, email=email, is_admin=is_first_user)
        if is_first_user:
            flash("Congratulations! As the first user, you have been made an admin.", "info")
            words = ["APPLE", "BRAIN", "CHAIR", "DELTA", "EAGLE", "FAITH", "GIANT", "HOUSE", "INPUT", "JOKER", "KNIFE", "LIGHT", "MONEY", "NURSE", "OCEAN", "PLANT", "QUEEN", "ROBOT", "SUGAR", "TIGER"]
            for w in words: db.session.add(Word(word=w))
            flash("Initial word list has been populated.", "success")

        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")

# Login Routes
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username, password = request.form["username"].strip(), request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.update({"user_id": user.id, "username": user.username, "is_admin": user.is_admin})
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

# Dashboard Routes
@main.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect(url_for("main.login"))
    return render_template("dashboard.html")

# Game Routes
@main.route("/play", methods=["GET", "POST"])
def play():
    if "user_id" not in session: return redirect(url_for("main.login"))
    today_start, today_end = datetime.combine(datetime.utcnow().date(), time.min), datetime.combine(datetime.utcnow().date(), time.max)
    games_today_count = Game.query.filter(Game.user_id == session['user_id'], Game.played_at.between(today_start, today_end)).count()
    if games_today_count >= 3:
        return render_template("play.html", limit_reached=True, history=[], game_over=True)

    if "target_word" not in session:
        words = Word.query.all()
        if not words: return redirect(url_for("main.dashboard"))
        word_obj = random.choice(words)
        session.update({"target_word": word_obj.word.upper(), "target_word_id": word_obj.id, "attempts": 0, "history": []})
    
    history, target = session.get("history", []), session.get("target_word")
    game_over, message, is_win = False, None, False

    if request.method == "POST":
        guess = request.form.get("guess", "").strip().upper()
        if not guess.isalpha() or len(guess) != 5:
            flash("Invalid input. Please enter a single 5-letter word.", "danger")
            return redirect(url_for("main.play"))
        if guess in ["".join([l['letter'] for l in a]) for a in history]:
            flash(f"You've already guessed '{guess}'.", "warning")
            return redirect(url_for("main.play"))
        db.session.add(Guess(guess_word=guess, user_id=session['user_id'], word_id=session['target_word_id']))
        session["attempts"] += 1
        history.append(check_guess(guess, target))
        session["history"] = history
        if guess == target or session["attempts"] >= 5:
            game_over = True
            is_win = guess == target
            message = f"You guessed it in {session['attempts']} attempts!" if is_win else "Better luck next time!"
            db.session.add(Game(user_id=session["user_id"], word=target, attempts=session["attempts"], won=is_win, played_at=datetime.utcnow()))
            db.session.commit()
            for key in ["target_word", "target_word_id", "attempts", "history"]: session.pop(key, None)

    return render_template("play.html", history=history, game_over=game_over, message=message, attempts=session.get('attempts', 0), is_win=is_win, secret_word=(target if game_over and not is_win else None), limit_reached=False)

def check_guess(guess, target):
    feedback, t_counts = [], {c: target.count(c) for c in set(target)}
    for i in range(5):
        if guess[i] == target[i]:
            feedback.append({"letter": guess[i], "color": "green"})
            t_counts[guess[i]] -= 1
        else:
            feedback.append({"letter": guess[i], "color": "grey"})
    for i in range(5):
        if feedback[i]['color'] != 'green' and guess[i] in target and t_counts.get(guess[i], 0) > 0:
            feedback[i]['color'] = 'orange'
            t_counts[guess[i]] -= 1
    return feedback

# Leaderboard Routes
@main.route("/leaderboard")
def leaderboard():
    if "user_id" not in session: return redirect(url_for("main.login"))
    stats = db.session.query(User.username, func.count(Game.id).label("games_played"), func.sum(case((Game.won == True, 1), else_=0)).label("wins")).join(Game, User.id == Game.user_id).group_by(User.id).order_by(func.sum(case((Game.won == True, 1), else_=0)).desc(), func.count(Game.id).asc()).all()
    user_games = Game.query.filter_by(user_id=session["user_id"]).all()
    wins = sum(1 for g in user_games if g.won)
    return render_template("leaderboard.html", leaderboard=stats, total_games=len(user_games), wins=wins, losses=(len(user_games) - wins), win_rate=(round((wins / len(user_games)) * 100, 2) if len(user_games) > 0 else 0))

# Admin Routes
@main.route("/admin")
@admin_required
def admin_dashboard():
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    today_end = datetime.combine(datetime.utcnow().date(), time.max)
    
    search_username = request.args.get('search_user', None)
    searched_user = None
    
    games_query = db.session.query(Game)

    if search_username:
        searched_user = User.query.filter(User.username.ilike(f'%{search_username}%')).first()
        if searched_user:
            games_query = games_query.filter(Game.user_id == searched_user.id)
        else:
            flash(f"User '{search_username}' not found. Showing site-wide stats.", 'warning')

    # Calculate stats based on the filtering
    games_today = games_query.filter(Game.played_at.between(today_start, today_end)).count()
    wins_today = games_query.filter(Game.played_at.between(today_start, today_end), Game.won == True).count()
    
    # These stats are static throught the flitering
    total_users = User.query.count()
    users_played_today_count = db.session.query(func.count(distinct(Game.user_id))).filter(Game.played_at.between(today_start, today_end)).scalar()
    
    all_users = User.query.order_by(User.created_at.desc()).all()
    all_words = Word.query.order_by(Word.word).all()
    
    # Fetch today's games based on the (potentially filtered) games query
    todays_games = games_query.filter(Game.played_at.between(today_start, today_end)).order_by(Game.played_at.desc()).all()

    return render_template(
        'admin_dashboard.html', 
        total_users=total_users, 
        users_played_today=users_played_today_count,
        games_today=games_today, 
        wins_today=wins_today,
        all_users=all_users,
        all_words=all_words,
        todays_games=todays_games,
        searched_user=searched_user
    )

@main.route("/admin/add-word", methods=['POST'])
@admin_required
def add_word():
    new_word = request.form.get('word', '').strip().upper()
    if not new_word.isalpha() or len(new_word) != 5:
        flash("Invalid entry. Word must be 5 letters long.", "danger")
    elif Word.query.filter_by(word=new_word).first():
        flash(f"The word '{new_word}' already exists.", "warning")
    else:
        db.session.add(Word(word=new_word))
        db.session.commit()
        flash(f"Successfully added '{new_word}'.", "success")
    return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/delete-word/<int:word_id>', methods=['POST'])
@admin_required
def delete_word(word_id):
    word_to_delete = Word.query.get(word_id)
    if word_to_delete:
        db.session.delete(word_to_delete)
        db.session.commit()
        flash(f"Successfully deleted '{word_to_delete.word}'.", "success")
    else:
        flash("Word not found.", "danger")
    return redirect(url_for('main.admin_dashboard'))

@main.route("/admin/chart-data")
@admin_required
def chart_data():
    user_id = request.args.get('user_id', None)
    query_base = db.session.query(Game)
    if user_id:
        query_base = query_base.filter(Game.user_id == user_id)

    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start, day_end = datetime.combine(day, time.min), datetime.combine(day, time.max)
        chart_labels.append(day.strftime("%b %d"))
        games_on_day = query_base.filter(Game.played_at.between(day_start, day_end)).count()
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