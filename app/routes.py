from flask import Blueprint
from . import db
from .models import Word

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return "Guess The Word - Flask with Databasee Connected"

@main.route("/add-words")
def add_words():
    sample_words=["APPLE","BRAIN","CHAIR","DELTA","EAGLE",
                  "FAITH","GIANT","HOUSE","INPUT","JOKER",
                  "KNIFE","LIGHT","MMONEY","NURSE","OCEAN",
                  "PLANT","QUEEN","ROBOT","SUGAR","TIGER"]
    for w in sample_words:
        if not Word.query.filter_by(word=w).first():
            new_word=Word(word=w)
            db.session.add(new_word)
    db.session.commit()
    return "20 words added successfully!"


