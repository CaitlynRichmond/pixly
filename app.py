import os
from dotenv import load_dotenv
from flask_caching import Cache
from flask import Flask, render_template, redirect, request, g
from werkzeug.utils import secure_filename
from upload_helpers import get_metadata
from gallery_helpers import (
    get_makes_and_models,
    get_filtered_photos,
    filter_by_make_and_model,
)
from s3 import s3_upload, s3_delete, s3_download
from PIL import Image
from image_conversions import edit_image
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
        image = form.image.data
        data = {
            k: v
            for k, v in form.data.items()
            if k != "csrf_token" and k != "image" and v != ""
        }

        filename = secure_filename(image.filename)
        content_type = image.content_type

        image.save(os.path.join(filename))
        image = Image.open(f"{filename}")
        dct = get_metadata(image)
        image.close()

        photo = Photo(exif=dct, **data)  # type: ignore
        db.session.add(photo)
        db.session.commit()

        # There's an issue with adding json and the conversion of some fields
        # to the null unicode character, so sanitizing the database is the fix
        # as the metadata can be nested multiple levels
        sql = text(
            """UPDATE photos set exif= REPLACE(exif::text, :val, '' )::json
            WHERE exif::text like :val2;"""
        )
        db.session.execute(sql, {"val": r"\u0000", "val2": r"%\u0000%"})
        db.session.commit()

        s3_upload(filename, str(photo.id), content_type)
        s3_upload(filename, f"{photo.id}-original", content_type)

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
def edit_image_route(id, edit):
    """Edit the image and upload to s3"""

    cache.clear()
    filename = f"{id}.png"

    s3_download(str(id), filename)

    image = Image.open(filename)
    new_image = edit_image(image, edit)
    image.close()

    new_image.save(os.path.join(filename))
    content_type = new_image.format
    s3_upload(filename, str(id), content_type)

    new_image.close()
    cache.clear()
    os.remove(filename)

    return redirect(f"/images/{id}")


@app.post("/images/<int:id>/revert")
def revert_image(id):
    """Revert image to original"""

    filename = f"{id}.png"

    s3_download(f"{id}-original", filename)

    image = Image.open(filename)
    content_type = image.format

    s3_upload(filename, str(id), content_type)

    cache.clear()
    image.close()
    os.remove(filename)

    return redirect(f"/images/{id}")


@app.post("/images/<int:id>/delete")
def delete_image(id):
    """Delete image and any copies"""

    s3_delete(f"{id}")
    s3_delete(f"{id}-original")

    Photo.query.filter_by(id=id).delete()
    db.session.commit()

    return redirect(f"/images")


@app.after_request
def add_header(response):
    """Handles caching so that images should show on button press"""

    response.cache_control.no_store = True
    response.headers[
        "Cache-Control"
    ] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response
