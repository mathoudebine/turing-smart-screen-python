from PIL import Image


def generate_sample_image(width, height):
    """Generates a sample image that has red, green, blue and black in each
    corner and the other pixels interpolated linearly."""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None

    for x in range(width):
        for y in range(height):
            # Calculate interpolation weights based on position
            wx = x / (width - 1)  # Horizontal weight (0 to 1)
            wy = y / (height - 1)  # Vertical weight (0 to 1)

            # Linear interpolation for each color channel
            r = int((1 - wx) * (1 - wy) * 255)  # Top-left (Red)
            g = int(wx * (1 - wy) * 255)       # Top-right (Green)
            b = int(wy * (1 - wx) * 255)       # Bottom-left (Blue)

            # Set the pixel value
            pixels[x, y] = (r, g, b)
    
    return img
