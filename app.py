import os
from dotenv import load_dotenv
import boto3
from flask_caching import Cache


from flask import Flask, render_template, redirect, request, g
from werkzeug.utils import secure_filename

from PIL import Image, TiffImagePlugin, ImageOps, ImageFilter


from PIL.ExifTags import TAGS
from forms import ImageForm, EXIFSearchForm, CSRFProtectForm
from models import db, connect_db, Photo
from sqlalchemy import text, or_


load_dotenv()


app = Flask(__name__)
cache = Cache(app)


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
                    print("K IS PRINTED HERE AAA     ", TAGS[k])
                    print("V IS PRINTED HERE AAA     ", v)
                    print("V IS TYPE", type(v))
                    dct[TAGS[k]] = v
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

        os.remove(filename)
        return redirect(f"/images/{photo.id}")

    return render_template("upload.html", form=form)


@app.get("/images/<int:id>")
def image_page(id):
    """Gets the specific image profile"""

    photo = Photo.query.get_or_404(id)

    return render_template("image-page.html", photo=photo)


@app.route("/images", methods=["GET", "POST"])
def image_gallery():
    search = request.args.get("q")

    if not search:
        photos = Photo.query.all()
    else:
        photos = Photo.query.filter(
            or_(
                Photo.by.ilike(f"%{search}%"),
                Photo.title.ilike(f"%{search}%"),
                Photo.caption.ilike(f"%{search}%"),
            )
        ).all()
    form = EXIFSearchForm()
    if form.validate_on_submit():
        print("test    make ", form.make.data)
        print("test   model ", form.model.data)
        model = form.model.data
        make = form.make.data
        print(make, "MAKE IS HERE AAA")
        if model != "Any":
            photos = [
                photo for photo in photos if photo.exif.get("Model") == model
            ]
        if make != "Any":
            photos = [
                photo for photo in photos if photo.exif.get("Make") == make
            ]

    # So I want photo EXIF data here, and I want to group them by the exif data names
    makes = set()
    models = set()
    for photo in photos:
        makes.add(photo.exif.get("Make"))
        models.add(photo.exif.get("Model"))

    if None in makes:
        makes.remove(None)

    if None in models:
        models.remove(None)

    # print("MAKES   ", makes)
    # print("MODELS   ", models)
    form.make.choices = ["Any", *makes]
    form.model.choices = ["Any", *models]

    return render_template(
        "image-gallery.html", form=form, search=search, photos=photos
    )


@app.route("/images/<int:id>/edit/<edit>", methods=["GET", "POST"])
def edit_image_test(id, edit):
    cache.clear()

    filename = f"{id}.png"

    s3.download_file(os.environ["AWS_BUCKET"], str(id), str(id))

    os.rename(str(id), filename)
    image = Image.open(filename)

    if edit == "flip":
        newImage = ImageOps.flip(image)
    elif edit == "mirror":
        newImage = ImageOps.mirror(image)
    elif edit == "blur":
        newImage = image.filter(ImageFilter.GaussianBlur(radius=8))
    else:
        newImage = image.filter(ImageFilter.GaussianBlur(radius=8))
    newImage.save(os.path.join(filename))
    content_type = image.format

    s3.upload_file(
        filename,
        os.environ["AWS_BUCKET"],
        str(id),
        ExtraArgs={
            "ContentType": f"{content_type}",
        },
    )

    os.remove(filename)

    return redirect(f"/images/{id}")
