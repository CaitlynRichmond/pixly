import os
from dotenv import load_dotenv
import boto3


from flask import Flask, render_template
from werkzeug.utils import secure_filename

from PIL import Image

# from PIL.ExifTags import TAGS
from forms import ImageForm
from models import db, connect_db

S3_BUCKET = os.environ["AWS_BUCKET"]
S3_SECRET_KEY = os.environ["AWS_SECRET_KEY"]
S3_ACCESS_KEY = os.environ["AWS_ACCESS_KEY"]


load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ECHO"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

connect_db(app)
db.create_all()

s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)


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

        # Exif data
        # exif = {}
        # for k, v in image.getexif().items():
        #     tag = TAGS.get(k)
        #     exif[tag] = v

        # photo = Photo(exif=exif)
        # print("!!!!!!", photo)

        s3.upload_file(
            filename,
            S3_BUCKET,
            filename,  # TODO: Make this something that's unique (maybe id once in db)
            ExtraArgs={
                "Metadata": {
                    "ContentType": f"{content_type}",
                }
            },
        )

        os.remove(filename)

    return render_template("upload.html", form=form)
