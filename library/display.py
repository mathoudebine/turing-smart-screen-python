from library import config
from library.lcd_comm_rev_a import LcdCommRevA, Orientation

THEME_DATA = config.THEME_DATA
CONFIG_DATA = config.CONFIG_DATA


def get_full_path(path, name):
    if name:
        return path + name
    else:
        return None


class Display:
    def __init__(self):
        self.lcd = None
        if CONFIG_DATA["display"]["REVISION"] == "A":
            self.lcd = LcdCommRevA()
        elif CONFIG_DATA["display"]["REVISION"] == "B":
            pass
        else:
            print("Unknown display revision '", CONFIG_DATA["display"]["REVISION"], "'")

    def initialize_display(self):
        # Clear screen (blank)
        self.lcd.SetOrientation(Orientation.PORTRAIT)  # Bug: orientation needs to be PORTRAIT before clearing
        self.lcd.Clear()

        # Set brightness
        self.lcd.SetBrightness()

        # Set orientation
        self.lcd.SetOrientation()

    def display_static_images(self):
        if THEME_DATA['static_images']:
            for image in THEME_DATA['static_images']:
                print(f"Drawing Image: {image}")
                self.lcd.DisplayBitmap(
                    bitmap_path=THEME_DATA['PATH'] + THEME_DATA['static_images'][image].get("PATH"),
                    x=THEME_DATA['static_images'][image].get("X", 0),
                    y=THEME_DATA['static_images'][image].get("Y", 0),
                    width=THEME_DATA['static_images'][image].get("WIDTH", 0),
                    height=THEME_DATA['static_images'][image].get("HEIGHT", 0)
                )

    def display_static_text(self):
        if THEME_DATA['static_text']:
            for text in THEME_DATA['static_text']:
                print(f"Drawing Text: {text}")
                self.lcd.DisplayText(
                    text=THEME_DATA['static_text'][text].get("TEXT"),
                    x=THEME_DATA['static_text'][text].get("X", 0),
                    y=THEME_DATA['static_text'][text].get("Y", 0),
                    font=THEME_DATA['static_text'][text].get("FONT", "roboto/Roboto-Regular.ttf"),
                    font_size=THEME_DATA['static_text'][text].get("FONT_SIZE", 10),
                    font_color=THEME_DATA['static_text'][text].get("FONT_COLOR", (0, 0, 0)),
                    background_color=THEME_DATA['static_text'][text].get("BACKGROUND_COLOR", (255, 255, 255)),
                    background_image=get_full_path(THEME_DATA['PATH'],
                                                   THEME_DATA['static_text'][text].get("BACKGROUND_IMAGE", None))
                )


display = Display()
