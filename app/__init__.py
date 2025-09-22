from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db=SQLAlchemy()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY']='supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///guessword.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

    db.init_app(app)
    bcrypt.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    return app

