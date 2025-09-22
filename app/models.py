from .import db
from datetime import datetime

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50),unique=True,nullable=False)
    password=db.Column(db.String(255),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

    guesses=db.relationship('Guess',backref='user',lazy=True,foreign_keys="Guess.user_id")

class Word(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    word=db.Column(db.String(5),unique=True,nullable=False)

    guesses=db.relationship('Guess',backref='word',lazy=True, foreign_keys="Guess.word_id")

class Guess(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    guess_word=db.Column(db.String(5),nullable=False)
    time_stamp=db.Column(db.DateTime,default=datetime.utcnow)

    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    word_id=db.Column(db.Integer,db.ForeignKey('word.id'),nullable=False)