# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Charles Ferguson (gerph)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import struct

from serial.tools.list_ports import comports

from library.lcd.lcd_comm import *
from library.log import logger


class Command(IntEnum):
    HELLO = 0xCA  # Establish communication before driving the screen
    SET_ORIENTATION = 0xCB  # Sets the screen orientation
    DISPLAY_BITMAP = 0xCC  # Displays an image on the screen
    SET_LIGHTING = 0xCD  # Sets the screen backplate RGB LED color
    SET_BRIGHTNESS = 0xCE  # Sets the screen brightness


# In revision B, basic orientations (portrait / landscape) are managed by the display
# The reverse orientations (reverse portrait / reverse landscape) are software-managed
class OrientationValueRevB(IntEnum):
    ORIENTATION_PORTRAIT = 0x0
    ORIENTATION_LANDSCAPE = 0x1


# HW revision B offers 4 sub-revisions to identify the HW capabilities
class SubRevision(IntEnum):
    A01 = 0xA01  # HW revision B - brightness 0/1
    A02 = 0xA02  # HW revision "flagship" - brightness 0/1
    A11 = 0xA11  # HW revision B - brightness 0-255
    A12 = 0xA12  # HW revision "flagship" - brightness 0-255


# This class is for XuanFang (rev. B & flagship) 3.5" screens
class LcdCommRevB(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: queue.Queue = None):
        logger.debug("HW revision: B")
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.openSerial()
        self.sub_revision = SubRevision.A01  # Run a Hello command to detect correct sub-rev.

    def __del__(self):
        self.closeSerial()

    def is_flagship(self):
        return self.sub_revision == SubRevision.A02 or self.sub_revision == SubRevision.A12

    def is_brightness_range(self):
        return self.sub_revision == SubRevision.A11 or self.sub_revision == SubRevision.A12

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()
        auto_com_port = None

        for com_port in com_ports:
            if com_port.serial_number == "2017-2-25":
                auto_com_port = com_port.device
                break

        return auto_com_port

    def SendCommand(self, cmd: Command, payload=None, bypass_queue: bool = False):
        # New protocol (10 byte packets, framed with the command, 8 data bytes inside)
        if payload is None:
            payload = [0] * 8
        elif len(payload) < 8:
            payload = list(payload) + [0] * (8 - len(payload))

        byteBuffer = bytearray(10)
        byteBuffer[0] = cmd
        byteBuffer[1] = payload[0]
        byteBuffer[2] = payload[1]
        byteBuffer[3] = payload[2]
        byteBuffer[4] = payload[3]
        byteBuffer[5] = payload[4]
        byteBuffer[6] = payload[5]
        byteBuffer[7] = payload[6]
        byteBuffer[8] = payload[7]
        byteBuffer[9] = cmd

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [byteBuffer]))

    def _hello(self):
        hello = [ord('H'), ord('E'), ord('L'), ord('L'), ord('O')]

        # This command reads LCD answer on serial link, so it bypasses the queue
        self.SendCommand(Command.HELLO, payload=hello, bypass_queue=True)
        response = self.lcd_serial.read(10)
        self.lcd_serial.flushInput()

        if len(response) != 10:
            logger.warning("Device not recognised (short response to HELLO)")
        assert response, "Device did not return anything"
        if response[0] != Command.HELLO or response[-1] != Command.HELLO:
            logger.warning("Device not recognised (bad framing)")
        if [x for x in response[1:6]] != hello:
            logger.warning("Device not recognised (No HELLO; got %r)" % (response[1:6],))
        # The HELLO response here is followed by 2 bytes
        # This is the screen version (not like the revision which is B/flagship)
        # The version is used to determine what capabilities the screen offers (see SubRevision class above)
        if response[6] == 0xA:
            if response[7] == 0x01:
                self.sub_revision = SubRevision.A01
            elif response[7] == 0x02:
                self.sub_revision = SubRevision.A02
            elif response[7] == 0x11:
                self.sub_revision = SubRevision.A11
            elif response[7] == 0x12:
                self.sub_revision = SubRevision.A12
            else:
                logger.warning("Display returned unknown sub-revision on Hello answer")

        logger.debug("HW sub-revision: %s" % (str(self.sub_revision)))

    def InitializeComm(self):
        self._hello()

    def Reset(self):
        # HW revision B does not implement a command to reset it: clear display instead
        self.Clear()

    def Clear(self):
        # HW revision B does not implement a Clear command: display a blank image on the whole screen
        # Force an orientation in case the screen is currently configured with one different from the theme
        backup_orientation = self.orientation
        self.SetOrientation(orientation=Orientation.PORTRAIT)

        blank = Image.new("RGB", (self.get_width(), self.get_height()), (255, 255, 255))
        self.DisplayPILImage(blank)

        # Restore orientation
        self.SetOrientation(orientation=backup_orientation)

    def ScreenOff(self):
        # HW revision B does not implement a "ScreenOff" native command: using SetBrightness(0) instead
        self.SetBrightness(0)

    def ScreenOn(self):
        # HW revision B does not implement a "ScreenOn" native command: using SetBrightness() instead
        self.SetBrightness()

    def SetBrightness(self, level: int = 25):
        assert 0 <= level <= 100, 'Brightness level must be [0-100]'

        if self.is_brightness_range():
            # Brightness scales from 0 to 255, with 255 being the brightest and 0 being the darkest.
            # Convert our brightness % to an absolute value.
            converted_level = int((level / 100) * 255)
        else:
            # Brightness is 1 (off) or 0 (full brightness)
            logger.info("Your display does not support custom brightness level")
            converted_level = 1 if level == 0 else 0

        self.SendCommand(Command.SET_BRIGHTNESS, payload=[converted_level])

    def SetBackplateLedColor(self, led_color: Tuple[int, int, int] = (255, 255, 255)):
        if isinstance(led_color, str):
            led_color = tuple(map(int, led_color.split(', ')))
        if self.is_flagship():
            self.SendCommand(Command.SET_LIGHTING, payload=list(led_color))
        else:
            logger.info("Only HW revision 'flagship' supports backplate LED color setting")

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        # In revision B, basic orientations (portrait / landscape) are managed by the display
        # The reverse orientations (reverse portrait / reverse landscape) are software-managed
        self.orientation = orientation
        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.REVERSE_PORTRAIT:
            self.SendCommand(Command.SET_ORIENTATION, payload=[OrientationValueRevB.ORIENTATION_PORTRAIT])
        else:
            self.SendCommand(Command.SET_ORIENTATION, payload=[OrientationValueRevB.ORIENTATION_LANDSCAPE])

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
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'

        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.LANDSCAPE:
            (x0, y0) = (x, y)
            (x1, y1) = (x + image_width - 1, y + image_height - 1)
        else:
            # Reverse landscape/portrait orientations are software-managed: get new coordinates
            (x0, y0) = (self.get_width() - x - image_width, self.get_height() - y - image_height)
            (x1, y1) = (self.get_width() - x - 1, self.get_height() - y - 1)

        self.SendCommand(Command.DISPLAY_BITMAP,
                         payload=[(x0 >> 8) & 255, x0 & 255,
                                  (y0 >> 8) & 255, y0 & 255,
                                  (x1 >> 8) & 255, x1 & 255,
                                  (y1 >> 8) & 255, y1 & 255])
        pix = image.load()
        line = bytes()

        # Lock queue mutex then queue all the requests for the image data
        with self.update_queue_mutex:
            for h in range(image_height):
                for w in range(image_width):
                    if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.LANDSCAPE:
                        R = pix[w, h][0] >> 3
                        G = pix[w, h][1] >> 2
                        B = pix[w, h][2] >> 3
                    else:
                        # Manage reverse orientations from software, because display does not manage it
                        R = pix[image_width - w - 1, image_height - h - 1][0] >> 3
                        G = pix[image_width - w - 1, image_height - h - 1][1] >> 2
                        B = pix[image_width - w - 1, image_height - h - 1][2] >> 3

                    # Color information is 0bRRRRRGGGGGGBBBBB
                    # Revision A: Encode in Little-Endian (native x86/ARM encoding)
                    # Revition B: Encode in Big-Endian
                    rgb = (R << 11) | (G << 5) | B
                    line += struct.pack('>H', rgb)

                    # Send image data by multiple of "display width" bytes
                    if len(line) >= self.get_width() * 8:
                        self.SendLine(line)
                        line = bytes()

            # Write last line if needed
            if len(line) > 0:
                self.SendLine(line)
