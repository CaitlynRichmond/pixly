import os
from dotenv import load_dotenv
import boto3


from flask import Flask, render_template, redirect, request
from werkzeug.utils import secure_filename

from PIL import Image, TiffImagePlugin

from PIL.ExifTags import TAGS
from forms import ImageForm
from models import db, connect_db, Photo
import json

load_dotenv()

app = Flask(__name__)

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
        out = json.dumps(dct)

        photo = Photo(exif=out)  # type: ignore
        db.session.add(photo)
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

    return render_template("image-page.html", id=photo.id)


@app.get("/images")
def image_gallery():
    search = request.args.get("q")

    if not search:
        photos = Photo.query.all()
    else:
        print("Function not implemented yet")
        # users = User.query.filter(User.username.like(f"%{search}%")).all()

    print("PHOTOS ", photos)

    ids = [photo.id for photo in photos]
    print("ids ", ids)
    return render_template("image-gallery.html", ids=ids)
