import os
from dotenv import load_dotenv
import boto3


from flask import Flask, render_template, request, flash, redirect
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.utils import secure_filename

from PIL import Image
from forms import ImageForm
from models import db, connect_db, Photo

AWS_BUCKET = os.environ["AWS_BUCKET"]
AWS_SECRET_KEY = os.environ["AWS_SECRET_KEY"]
AWS_ACCESS_KEY = os.environ["AWS_ACCESS_KEY"]


load_dotenv()

app = Flask(__name__)

app.config["S3_LOCATION"] = "http://{}.s3.amazonaws.com/".format(AWS_BUCKET)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ECHO"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

connect_db(app)


s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Handles upload page which should both show the upload form and on POST
    upload the image to AWS and take out the EXIF data to go to the database
    """

    form = ImageForm()

    if form.is_submitted():
        # Image is a werkzeug.FileStorage
        image = form.image.data
        filename = secure_filename(image.filename)

        # Gets the images content type (attribute of the werkzeug.FileStorage type)
        # This is passed to amazon so that it exists in the metadata there
        # and we can then open it by link
        content_type = image.content_type

        # We're join the image with the path name manipulation
        # using the werkzeug method save, which saves the file to a destination
        # path or object
        image.save(os.path.join(filename))

        # Opens and identifies the given image file giving it the file name r
        # image is an Image object now
        image = Image.open(f"{filename}")

        s3.upload_file(
            filename,
            "pixly-cait",
            filename,  # TODO: Make this something that's unique (maybe id once in db)
            ExtraArgs={"Metadata": {"ContentType": f"{content_type}"}},
        )
        os.remove(filename)

    return render_template("upload.html", form=form)
