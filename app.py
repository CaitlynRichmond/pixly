import os
from dotenv import load_dotenv
import boto3
from flask_caching import Cache


from flask import Flask, render_template, redirect, request, g
from werkzeug.utils import secure_filename
from gallery_helpers import (
    get_makes_and_models,
    get_filtered_photos,
    filter_by_make_and_model,
)

from PIL import Image, TiffImagePlugin
from image_conversions import edit_image
from PIL.ExifTags import TAGS
from forms import ImageForm, EXIFSearchForm, CSRFProtectForm
from models import db, connect_db, Photo
from sqlalchemy import text


load_dotenv()


app = Flask(__name__)
cache = Cache(app)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ECHO"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

connect_db(app)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
    aws_secret_access_key=os.environ["AWS_SECRET_KEY"],
)

db.create_all()


@app.before_request
def add_csrf_form_to_g():
    """Add a csrf form to Flask global"""

    g.csrf_form = CSRFProtectForm()


@app.get("/")
def homepage():
    """Show homepage"""

    return render_template("homepage.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Handles upload page which should both show the upload form and on POST
    upload the image to AWS and take out the EXIF data to go to the database
    """

    form = ImageForm()

    if form.validate_on_submit():
        # Image is a werkzeug.FileStorage based on the enc type on the form
        image = form.image.data
        data = {
            k: v
            for k, v in form.data.items()
            if k != "csrf_token" and k != "image" and v != ""
        }
        filename = secure_filename(image.filename)

        # Gets the images content type (attribute of the werkzeug.FileStorage type)
        # This is passed to amazon so that it exists in the metadata there
        # and we can then open it by link
        content_type = image.content_type

        # We're joining the image with the path name manipulation
        # using the werkzeug method save, which saves the file to a destination
        # path or object. So we're saving it to our directory
        image.save(os.path.join(filename))

        # Opens image in the same directory as the code, meaning it's path
        # is file name!
        image = Image.open(f"{filename}")

        # Exif data code from https://github.com/python-pillow/Pillow/issues/6199
        # As you cannot cast from the standard output EXIF format to JSON
        dct = {}

        def cast(v):
            if isinstance(v, TiffImagePlugin.IFDRational):
                return float(v)
            elif isinstance(v, tuple):
                return tuple(cast(t) for t in v)
            elif isinstance(v, bytes):
                return v.decode(errors="replace")
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    v[kk] = cast(vv)
                return v
            else:
                return v

        if image._getexif() != None:  # type: ignore as method exists
            for k, v in image._getexif().items():  # type: ignore as method exists
                if k in TAGS:
                    v = cast(v)
                    dct[TAGS[k]] = v
        image.close()
        photo = Photo(exif=dct, **data)  # type: ignore
        db.session.add(photo)
        db.session.commit()
        sql = text(
            """UPDATE photos set exif= REPLACE(exif::text, :val, '' )::json
            WHERE exif::text like :val2;"""
        )
        db.session.execute(sql, {"val": r"\u0000", "val2": r"%\u0000%"})
        db.session.commit()

        s3.upload_file(
            filename,
            os.environ["AWS_BUCKET"],
            str(photo.id),
            ExtraArgs={
                "ContentType": f"{content_type}",
            },
        )

        s3.upload_file(
            filename,
            os.environ["AWS_BUCKET"],
            f"{photo.id}-original",
            ExtraArgs={
                "ContentType": f"{content_type}",
            },
        )

        os.remove(filename)
        return redirect(f"/images/{photo.id}")

    return render_template("upload.html", form=form)


@app.get("/images/<int:id>")
def image_page(id):
    """Gets the specific image profile and passes the edit options for the buttons"""

    photo = Photo.query.get_or_404(id)

    edit_options = [
        "flip",
        "mirror",
        "blur",
        "grayscale",
        "auto-contrast",
        "invert",
        "sepia",
    ]

    return render_template(
        "image-page.html", photo=photo, edit_options=edit_options
    )


@app.route("/images", methods=["GET", "POST"])
def image_gallery():
    """Displays image gallery and filtering by metadata for make and model for
    images that have that data"""

    search = request.args.get("q", "")
    search = str(search).strip()

    if not search:
        photos = Photo.query.all()
    else:
        photos = get_filtered_photos(search)
    form = EXIFSearchForm()
    if form.validate_on_submit():
        model = form.model.data
        make = form.make.data
        photos = filter_by_make_and_model(photos, make, model)

    makes, models = get_makes_and_models(photos)

    form.make.choices = ["Any", *makes]
    form.model.choices = ["Any", *models]

    return render_template(
        "image-gallery.html", form=form, search=search, photos=photos
    )


@app.post("/images/<int:id>/edit/<edit>")
def edit_image_test(id, edit):
    cache.clear()
    # can't do the rgb ops to non png
    filename = f"{id}.png"

    s3.download_file(os.environ["AWS_BUCKET"], str(id), filename)

    image = Image.open(filename)

    new_image = edit_image(image, edit)
    image.close()

    new_image.save(os.path.join(filename))
    content_type = new_image.format

    s3.upload_file(
        filename,
        os.environ["AWS_BUCKET"],
        str(id),
        ExtraArgs={
            "ContentType": f"{content_type}",
        },
    )

    new_image.close()
    cache.clear()

    os.remove(filename)

    return redirect(f"/images/{id}")


@app.post("/images/<int:id>/revert")
def revert_image(id):
    """Revert image to original"""
    filename = f"{id}.png"

    s3.download_file(os.environ["AWS_BUCKET"], f"{id}-original", filename)
    image = Image.open(filename)
    content_type = image.format
    s3.upload_file(
        filename,
        os.environ["AWS_BUCKET"],
        str(id),
        ExtraArgs={
            "ContentType": f"{content_type}",
        },
    )
    cache.clear()

    image.close()

    os.remove(filename)

    return redirect(f"/images/{id}")


@app.post("/images/<int:id>/delete")
def delete_image(id):
    """Delete image and any copies"""
    s3.delete_object(Bucket=os.environ["AWS_BUCKET"], Key=f"{id}")
    s3.delete_object(Bucket=os.environ["AWS_BUCKET"], Key=f"{id}-original")

    Photo.query.filter_by(id=id).delete()
    db.session.commit()

    return redirect(f"/images")


@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers[
        "Cache-Control"
    ] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response
