from flask_wtf import FlaskForm
from wtforms import StringField, RadioField
from wtforms.validators import Optional

from flask_wtf.file import FileField, FileRequired

# from werkzeug.utils import secure_filename


class ImageForm(FlaskForm):
    """Form for adding an image"""

    image = FileField(
        "File",
        validators=[
            FileRequired(),
        ],
    )
    title = StringField("Title", validators=[Optional()])
    caption = StringField("Caption", validators=[Optional()])
    by = StringField("By", validators=[Optional()])


class EXIFSearchForm(FlaskForm):
    """Form for searching EXIF Data, choices are dynamically created"""

    make = RadioField(
        "Make", choices=[], default="Any", validate_choice=False
    )
    model = RadioField(
        "Model", choices=[], default="Any", validate_choice=False
    )


class CSRFProtectForm(FlaskForm):
    """Form for CSRF validation, used on the editing page"""
