"""SQLAlchemy models for Pix.ly."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON


db = SQLAlchemy()


class Photo(db.Model):
    """Database of photo EXIF data"""

    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, default="Untitled", nullable=False)
    caption = db.Column(db.Text, default="No caption", nullable=False)
    by = db.Column(db.Text, default="Unknown", nullable=False)
    exif = db.Column(JSON, nullable=False)


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    app.app_context().push()
    db.app = app
    db.init_app(app)
