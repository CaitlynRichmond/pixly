from PIL.ExifTags import TAGS
from PIL import TiffImagePlugin


def get_metadata(image):
    """get the EXIF data from the image"""
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

    if image._getexif() != None:
        for k, v in image._getexif().items():
            if k in TAGS:
                v = cast(v)
                dct[TAGS[k]] = v

    return dct
