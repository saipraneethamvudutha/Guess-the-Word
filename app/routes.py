from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User, Word, Guess
import re
from collections import Counter
import random 

main = Blueprint("main", __name__)

# Home route
@main.route("/")
def home():
    return render_template("home.html")

# Register route
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

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

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("main.login"))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")

# Login route
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
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

@main.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("main.login"))
    return render_template("dashboard.html", username=session.get("username"))


@main.route("/add-words")
def add_words():
    words_to_add = [
        "APPLE", "HOUSE", "TOWER", "FLASK", "PYTHON", "GRACE", "STYLE", "BEACH", 
        "CHAIR", "TABLE", "MUSIC", "WATER", "HEART", "LIGHT", "WORLD", "HAPPY", 
        "SMILE", "QUIET", "DREAM", "PLANT"
    ]
    for w in words_to_add:
        # Check if the word already exists to avoid duplicates
        if not Word.query.filter_by(word=w).first():
            db.session.add(Word(word=w))
    db.session.commit()
    flash(f"Added {len(words_to_add)} words to the database!", "success")
    return redirect(url_for('main.home'))

def check_guess(guess, secret_word):
    """Checks a guess and returns feedback with colors."""
    feedback = []
    secret_counts = Counter(secret_word)
    
    for i in range(5):
        if guess[i] == secret_word[i]:
            feedback.append({'letter': guess[i], 'color': 'green'})
            secret_counts[guess[i]] -= 1
        else:
            feedback.append({'letter': guess[i], 'color': 'grey'})

    for i in range(5):
        if feedback[i]['color'] != 'green':
            if guess[i] in secret_word and secret_counts[guess[i]] > 0:
                feedback[i]['color'] = 'orange'
                secret_counts[guess[i]] -= 1
    return feedback

# Play Route
@main.route("/play", methods=['GET', 'POST'])
def play():
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    if 'word_id' not in session:
        all_words = Word.query.all()
        if not all_words:
            flash("No words in the database to play with! Visit /add-words first.", "warning")
            return redirect(url_for('main.dashboard'))
        random_word = random.choice(all_words)
        session['word_id'] = random_word.id
        session['guesses'] = [] 

    secret_word_obj = Word.query.get(session['word_id'])
    secret_word = secret_word_obj.word
    
    history = session.get('guesses', [])
    game_over = False
    message = ""

    if request.method == 'POST':
        guess = request.form.get('guess', '').upper() 

        if len(guess) != 5 or not guess.isalpha():
            flash("Your guess must be a 5-letter word.", "danger")
        else:
            feedback = check_guess(guess, secret_word)
            history.append(feedback)
            session['guesses'] = history
            new_db_guess = Guess(guess_word=guess, user_id=session['user_id'], word_id=session['word_id'])
            db.session.add(new_db_guess)
            db.session.commit()
            if guess == secret_word:
                message = f"You won! The word was {secret_word}."
                game_over = True
                session.pop('word_id') 
            elif len(history) >= 5:
                message = f"Game over! The secret word was {secret_word}."
                game_over = True
                session.pop('word_id')
    
    return render_template("play.html", history=history, game_over=game_over, message=message)