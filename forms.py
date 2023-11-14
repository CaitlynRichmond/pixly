from flask_wtf import FlaskForm

# from wtforms.validators import InputRequired
from flask_wtf.file import FileField, FileRequired, FileAllowed

# from werkzeug.utils import secure_filename


class ImageForm(FlaskForm):
    """Form for adding an image"""

    image = FileField(
        "File",
        validators=[
            FileRequired(),
            FileAllowed(
                ["pdf", "png", "jpg", "jpeg", "heic"],
                "Invalid File Type. Must be .heic, .pdf, .jpg, .png, .jpeg",
            ),
        ],
    )
