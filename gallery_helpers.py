from models import Photo
from sqlalchemy import or_


def get_makes_and_models(photos):
    """Gets the makes and models from all the photos and returns them"""

    makes = set()
    models = set()
    for photo in photos:
        makes.add(photo.exif.get("Make"))
        models.add(photo.exif.get("Model"))

    if None in makes:
        makes.remove(None)

    if None in models:
        models.remove(None)

    return makes, models


def get_filtered_photos(search):
    """Queries database for filtered photos"""

    return Photo.query.filter(
        or_(
            Photo.by.ilike(f"%{search}%"),
            Photo.title.ilike(f"%{search}%"),
            Photo.caption.ilike(f"%{search}%"),
        )
    ).all()


def filter_by_make_and_model(photos, make, model):
    """Filters photos by make and model if they're not the default radio button
    selection"""

    if model != "Any":
        photos = [
            photo for photo in photos if photo.exif.get("Model") == model
        ]
    if make != "Any":
        photos = [
            photo for photo in photos if photo.exif.get("Make") == make
        ]

    return photos
