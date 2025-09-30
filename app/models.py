from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    games = db.relationship('Game', backref='user', lazy=True)
    guesses = db.relationship('Guess', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(5), unique=True, nullable=False)

    guesses = db.relationship('Guess', backref='word', lazy=True)


class Guess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guess_word = db.Column(db.String(5), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('word.id'), nullable=False)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    word = db.Column(db.String(5), nullable=False)
    attempts = db.Column(db.Integer, nullable=False)
    won = db.Column(db.Boolean, default=False)
    played_at = db.Column(db.DateTime, nullable=False)