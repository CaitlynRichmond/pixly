"""SQLAlchemy models for Pix.ly."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class PhotoData(db.Model):
    """Database of photo EXIF data"""

    __tablename__ = "photodata"



def connect_db(app):
    
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    app.app_context().push()
    db.app = app
    db.init_app(app)
