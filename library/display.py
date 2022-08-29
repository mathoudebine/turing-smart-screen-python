from library import config
from library.lcd_comm_rev_a import LcdCommRevA
from library.lcd_comm_rev_b import LcdCommRevB

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
            self.lcd = LcdCommRevB()
        else:
            print("Unknown display revision '", CONFIG_DATA["display"]["REVISION"], "'")

    def initialize_display(self):
        # Reset screen in case it was in an unstable state (screen is also cleared)
        self.lcd.Reset()

        # Send initialization commands
        self.lcd.InitializeComm()

        # Set brightness
        self.lcd.SetBrightness()

        # Set backplate RGB LED color (for supported HW only)
        self.lcd.SetBackplateLedColor()

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
                    font=THEME_DATA['static_text'][text].get("FONT", "roboto-mono/RobotoMono-Regular.ttf"),
                    font_size=THEME_DATA['static_text'][text].get("FONT_SIZE", 10),
                    font_color=THEME_DATA['static_text'][text].get("FONT_COLOR", (0, 0, 0)),
                    background_color=THEME_DATA['static_text'][text].get("BACKGROUND_COLOR", (255, 255, 255)),
                    background_image=get_full_path(THEME_DATA['PATH'],
                                                   THEME_DATA['static_text'][text].get("BACKGROUND_IMAGE", None))
                )


display = Display()
