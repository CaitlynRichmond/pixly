from PIL import Image, TiffImagePlugin, ImageOps, ImageFilter


def edit_image(image, edit):
    """edit the image"""
    if edit == "flip":
        new_image = ImageOps.flip(image)
    elif edit == "mirror":
        new_image = ImageOps.mirror(image)
    elif edit == "blur":
        new_image = image.filter(ImageFilter.GaussianBlur(radius=8))
    elif edit == "invert":
        try:
            new_image = ImageOps.invert(image)
        except OSError:
            new_image = ImageOps.invert(image.convert("RGB"))
    elif edit == "auto-contrast":
        try:
            new_image = ImageOps.autocontrast(image)
        except OSError:
            new_image = ImageOps.autocontrast(image.convert("RGB"))
    elif edit == "grayscale":
        new_image = ImageOps.grayscale(image)
    else:
        new_image = image

    return new_image


# https://www.codementor.io/@isaib.cicourel/intermediate-image-filters-mj6y7abx4
# Sepia is a filter based on exagerating red, yellow and brown tones
# This implementation exagerates mainly yellow with a little brown
def get_sepia_pixel(red, green, blue, alpha):
    # This is a really popular implementation
    tRed = get_max((0.759 * red) + (0.398 * green) + (0.194 * blue))
    tGreen = get_max((0.676 * red) + (0.354 * green) + (0.173 * blue))
    tBlue = get_max((0.524 * red) + (0.277 * green) + (0.136 * blue))

    # Return sepia color
    return tRed, tGreen, tBlue, alpha


# Convert an image to sepia
def convert_sepia(image):
    # Get size
    width, height = image.size

    # Create new Image and a Pixel Map
    new = create_image(width, height)
    pixels = new.load()

    # Convert each pixel to sepia
    for i in range(0, width, 1):
        for j in range(0, height, 1):
            p = get_pixel(image, i, j)
            pixels[i, j] = get_sepia_pixel(p[0], p[1], p[2], 255)

    # Return new image
    return new
