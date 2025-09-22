from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db=SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SERECT_KEY']='supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///guessword.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.drop_all()
        db.create_all()

    return app

