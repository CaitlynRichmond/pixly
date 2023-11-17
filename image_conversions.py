from PIL import ImageOps, ImageFilter, ImagePalette


def edit_image(image, edit):
    """edit the image with the selected option.
    Returns original image if unfamiliar edit is passed"""
    if edit == "flip":
        new_image = ImageOps.flip(image)
    elif edit == "mirror":
        new_image = ImageOps.mirror(image)
    elif edit == "blur":
        new_image = image.filter(ImageFilter.GaussianBlur(radius=8))
    elif edit == "invert":
        try:
            new_image = ImageOps.invert(image)
        except (OSError, NotImplementedError):
            new_image = ImageOps.invert(image.convert("RGB"))
    elif edit == "auto-contrast":
        try:
            new_image = ImageOps.autocontrast(image)
        except (OSError, NotImplementedError):
            new_image = ImageOps.autocontrast(image.convert("RGB"))
    elif edit == "grayscale":
        new_image = ImageOps.grayscale(image)
    elif edit == "sepia":
        palette = ImagePalette.sepia()
        new_image = image.convert("P")
        new_image.putpalette(palette)
    else:
        new_image = image

    return new_image
