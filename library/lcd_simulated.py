from library.lcd_comm import *


class LcdSimulated(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: queue.Queue = None):
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.screen_image = Image.new("RGB", (self.get_width(), self.get_height()), (255, 255, 255))
        self.screen_image.save("screencap.png", "PNG")
        self.orientation = Orientation.PORTRAIT

    @staticmethod
    def auto_detect_com_port():
        return None

    def InitializeComm(self):
        pass

    def Reset(self):
        self.Clear()

    def Clear(self):
        self.SetOrientation(self.orientation)

    def ScreenOff(self):
        pass

    def ScreenOn(self):
        pass

    def SetBrightness(self, level: int = 25):
        pass

    def SetBackplateLedColor(self, led_color: tuple[int, int, int] = (255, 255, 255)):
        pass

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        # Just draw the screen again with the new width/height based on orientation
        with self.update_queue_mutex:
            self.screen_image = Image.new("RGB", (self.get_width(), self.get_height()), (255, 255, 255))
            self.screen_image.save("screencap.png", "PNG")

    def DisplayPILImage(
            self,
            image: Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        # If the image height/width isn't provided, use the native image size
        if not image_height:
            image_height = image.size[1]
        if not image_width:
            image_width = image.size[0]

        # If our image is bigger than our display, resize it to fit our screen
        if image.size[1] > self.get_height():
            image_height = self.get_height()
        if image.size[0] > self.get_width():
            image_width = self.get_width()

        assert x <= self.get_width(), 'Image X coordinate must be <= display width'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image width must be > 0'
        assert image_width > 0, 'Image height must be > 0'

        with self.update_queue_mutex:
            self.screen_image.paste(image, (x, y))
            self.screen_image.save("screencap.png", "PNG")
