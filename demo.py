#!/usr/bin/env python3
# Enhanced Turing Smart Screen Demo with Rotating Background Images
# Based on turing-smart-screen-python library

import os
import signal
import sys
import time
import glob
import random
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from threading import Thread, Event

# Import LCD communication modules
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_comm_rev_c import LcdCommRevC
from library.lcd.lcd_comm_rev_d import LcdCommRevD
from library.lcd.lcd_simulated import LcdSimulated
from library.log import logger

# Configuration
COM_PORT = "AUTO"  # Set your COM port or "AUTO" for auto-discovery
REVISION = "A"     # Display revision (A, B, C, D, or SIMU)
WIDTH, HEIGHT = 320, 480  # Display dimensions in portrait mode
IMAGE_ROTATION_INTERVAL = 30  # Seconds between background changes
IMAGES_DIRECTORY = "images"   # Directory to scan for images

# Global variables
stop_event = Event()
lcd_comm = None
current_background = None
last_background = None  # Track when background actually changes

class ImageManager:
    """Handles image loading, resizing, and rotation"""

    def __init__(self, images_dir, display_width, display_height):
        self.images_dir = images_dir
        self.display_width = display_width
        self.display_height = display_height
        self.image_list = []
        self.current_index = 0
        self.load_images()

    def load_images(self):
        """Scan directory for supported image files"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
            logger.warning(f"Created images directory: {self.images_dir}")
            logger.info("Please add some images (PNG, JPG, JPEG, BMP) to the images directory")
            return

        # Supported image extensions
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']

        for ext in extensions:
            self.image_list.extend(glob.glob(os.path.join(self.images_dir, ext)))
            self.image_list.extend(glob.glob(os.path.join(self.images_dir, ext.upper())))

        if not self.image_list:
            logger.warning(f"No images found in {self.images_dir} directory")
            # Create a default image if none found
            self.create_default_image()
        else:
            logger.info(f"Found {len(self.image_list)} images in {self.images_dir}")
            # Shuffle the list for random order
            random.shuffle(self.image_list)

    def create_default_image(self):
        """Create a default gradient background if no images are found"""
        default_path = os.path.join(self.images_dir, "default_background.png")

        # Create a gradient background
        img = Image.new('RGB', (self.display_width, self.display_height))
        draw = ImageDraw.Draw(img)

        # Create vertical gradient from blue to purple
        for y in range(self.display_height):
            ratio = y / self.display_height
            r = int(50 + (150 * ratio))
            g = int(100 - (50 * ratio))
            b = int(200 + (55 * ratio))
            draw.line([(0, y), (self.display_width, y)], fill=(r, g, b))

        # Add some text
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        text = "Demo Background"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.display_width - text_width) // 2
        y = (self.display_height - text_height) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        img.save(default_path)
        self.image_list = [default_path]
        logger.info(f"Created default background: {default_path}")

    def resize_image_proportional(self, image_path):
        """Resize image to fit screen while maintaining aspect ratio"""
        try:
            logger.debug(f"Processing image: {image_path}")
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    logger.debug(f"Converting image from {img.mode} to RGB")
                    img = img.convert('RGB')

                orig_width, orig_height = img.size
                logger.debug(f"Original dimensions: {orig_width}x{orig_height}")

                # Calculate scaling factor to fit within display bounds
                scale_x = self.display_width / orig_width
                scale_y = self.display_height / orig_height
                scale = min(scale_x, scale_y)  # Use smaller scale to fit entirely
                logger.debug(f"Scale factors: x={scale_x:.3f}, y={scale_y:.3f}, chosen={scale:.3f}")

                # Calculate new dimensions
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                logger.debug(f"Scaled dimensions: {new_width}x{new_height}")

                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Create final image with display dimensions and center the resized image
                final_img = Image.new('RGB', (self.display_width, self.display_height), (0, 0, 0))
                paste_x = (self.display_width - new_width) // 2
                paste_y = (self.display_height - new_height) // 2
                logger.debug(f"Centering image at: ({paste_x}, {paste_y})")
                final_img.paste(resized_img, (paste_x, paste_y))

                # Save processed image
                processed_path = os.path.join(self.images_dir, f"processed_{os.path.basename(image_path)}")
                final_img.save(processed_path)
                logger.debug(f"Saved processed image: {processed_path}")

                logger.info(f"Resized {os.path.basename(image_path)}: {orig_width}x{orig_height} -> {new_width}x{new_height}")
                return processed_path

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None

    def get_next_image(self):
        """Get the next image in rotation"""
        if not self.image_list:
            return None

        image_path = self.image_list[self.current_index]
        processed_path = self.resize_image_proportional(image_path)

        self.current_index = (self.current_index + 1) % len(self.image_list)
        return processed_path if processed_path else image_path

def initialize_display():
    """Initialize the LCD communication"""
    global lcd_comm

    # Build LcdComm object based on hardware revision
    if REVISION == "A":
        logger.info("Selected Hardware Revision A (Turing Smart Screen 3.5\" & UsbPCMonitor 3.5\"/5\")")
        lcd_comm = LcdCommRevA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "B":
        logger.info("Selected Hardware Revision B (XuanFang screen 3.5\" version B / flagship)")
        lcd_comm = LcdCommRevB(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "C":
        logger.info("Selected Hardware Revision C (Turing Smart Screen 5\")")
        lcd_comm = LcdCommRevC(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "D":
        logger.info("Selected Hardware Revision D (Kipye Qiye Smart Display 3.5\")")
        lcd_comm = LcdCommRevD(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "SIMU":
        logger.info("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=WIDTH, display_height=HEIGHT)
    else:
        logger.error("Unknown revision")
        sys.exit(1)

    # Initialize display
    lcd_comm.Reset()
    lcd_comm.InitializeComm()
    lcd_comm.SetBrightness(level=50)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))
    lcd_comm.SetOrientation(orientation=Orientation.LANDSCAPE)

def display_demo_content(background_image, force_background_refresh=False):
    """Display various demo content on the screen"""
    global last_background

    if not background_image or not os.path.exists(background_image):
        logger.warning(f"Background image not found or invalid: {background_image}")
        return

    try:
        # Only refresh background if it changed or forced
        background_changed = last_background != background_image
        if background_changed or force_background_refresh:
            logger.debug(f"Refreshing background: {os.path.basename(background_image)}")
            start_bg = time.perf_counter()
            lcd_comm.DisplayBitmap(background_image)
            last_background = background_image
            end_bg = time.perf_counter()
            logger.debug(f"Background display took: {end_bg - start_bg:.3f}s")

        # Current time (updates frequently)
        current_time = datetime.now().strftime("%H:%M:%S")
        lcd_comm.DisplayText(current_time,
                           lcd_comm.get_width() - 120, 5,
                           font_size=20,
                           font_color=(255, 255, 255),
                           background_image=background_image)

        # Only redraw static content when background changes
        if background_changed or force_background_refresh:
            logger.debug("Redrawing static content due to background change")

            # Current date (static for the day)
            current_date = datetime.now().strftime("%Y-%m-%d")
            logger.debug(f"Displaying date: {current_date}")
            lcd_comm.DisplayText(current_date,
                               lcd_comm.get_width() - 120, 30,
                               font_size=16,
                               font_color=(200, 200, 200),
                               background_image=background_image)

            # Demo title (static)
            logger.debug("Displaying demo title")
            lcd_comm.DisplayText("Turing Smart Screen Demo", 10, 10,
                               font_size=18,
                               font_color=(255, 255, 0),
                               background_color=(0, 0, 0))

            # System info labels (static)
            logger.debug("Displaying system info labels")
            lcd_comm.DisplayText("CPU:", 10, 50,
                               font_size=16,
                               font_color=(255, 255, 255),
                               background_image=background_image)

            lcd_comm.DisplayText("GPU:", 10, 75,
                               font_size=16,
                               font_color=(255, 255, 255),
                               background_image=background_image)

            lcd_comm.DisplayText("RAM:", 10, 100,
                               font_size=16,
                               font_color=(255, 255, 255),
                               background_image=background_image)

        logger.debug("Demo content display completed successfully")

    except Exception as e:
        logger.error(f"Error displaying content: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")

def display_progress_bars(background_image, frame_count, force_refresh=False):
    """Display animated progress bars"""
    try:
        # CPU Usage bar - animated values
        cpu_value = int(50 + 30 * abs(math.sin(frame_count * 0.1)))
        if frame_count % 5 == 0 or force_refresh:  # Update every 5 frames to reduce flicker
            logger.debug(f"CPU value: {cpu_value}%")
            lcd_comm.DisplayProgressBar(80, 50,
                                      width=120, height=15,
                                      min_value=0, max_value=100, value=cpu_value,
                                      bar_color=(255, 100, 100), bar_outline=True,
                                      background_image=background_image)

            # Display CPU temperature
            cpu_temp = int(45 + 15 * abs(math.sin(frame_count * 0.12)))
            lcd_comm.DisplayText(f"{cpu_temp}°C", 210, 48,
                               font_size=14,
                               font_color=(255, 100, 100),
                               background_image=background_image)

        # GPU Usage bar
        gpu_value = int(60 + 25 * abs(math.cos(frame_count * 0.08)))
        if frame_count % 5 == 0 or force_refresh:
            logger.debug(f"GPU value: {gpu_value}%")
            lcd_comm.DisplayProgressBar(80, 75,
                                      width=120, height=15,
                                      min_value=0, max_value=100, value=gpu_value,
                                      bar_color=(100, 255, 100), bar_outline=True,
                                      background_image=background_image)

            # Display GPU temperature
            gpu_temp = int(62 + 18 * abs(math.cos(frame_count * 0.09)))
            lcd_comm.DisplayText(f"{gpu_temp}°C", 210, 73,
                               font_size=14,
                               font_color=(255, 165, 0),
                               background_image=background_image)

        # RAM Usage bar
        ram_value = int(40 + 20 * abs(math.sin(frame_count * 0.05)))
        if frame_count % 5 == 0 or force_refresh:
            logger.debug(f"RAM value: {ram_value}%")
            lcd_comm.DisplayProgressBar(80, 100,
                                      width=120, height=15,
                                      min_value=0, max_value=100, value=ram_value,
                                      bar_color=(100, 100, 255), bar_outline=True,
                                      background_image=background_image)

            # Display RAM usage in GB
            ram_used = 8.2 + (ram_value / 100) * 4
            lcd_comm.DisplayText(f"{ram_used:.1f}/16GB", 210, 98,
                               font_size=14,
                               font_color=(0, 191, 255),
                               background_image=background_image)

        # Radial progress bar (temperature gauge) - update less frequently
        if frame_count % 10 == 0 or force_refresh:
            temp_value = int(45 + 20 * abs(math.sin(frame_count * 0.03)))
            logger.debug(f"Temperature gauge value: {temp_value}°C")

            # Position radial gauge better
            gauge_x = lcd_comm.get_width() - 100
            gauge_y = 150

            lcd_comm.DisplayRadialProgressBar(gauge_x, gauge_y, 35, 6,
                                            min_value=0, max_value=100,
                                            value=temp_value,
                                            angle_start=135, angle_end=45,
                                            clockwise=True,
                                            bar_color=(255, 255, 0),
                                            text=f"SYS\n{temp_value}°C",
                                            font_size=12,
                                            font_color=(255, 255, 255),
                                            background_image=background_image)

        if frame_count % 20 == 0:
            logger.debug("Progress bars display completed successfully")

    except Exception as e:
        logger.error(f"Error displaying progress bars: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")

def background_rotation_thread(image_manager):
    """Thread function for rotating background images"""
    global current_background

    logger.debug("Background rotation thread started")

    while not stop_event.is_set():
        try:
            logger.debug("Getting next background image...")
            new_background = image_manager.get_next_image()
            if new_background:
                current_background = new_background
                logger.info(f"Switched to background: {os.path.basename(new_background)}")
                logger.debug(f"Full path: {new_background}")
            else:
                logger.warning("Failed to get next background image")
        except Exception as e:
            logger.error(f"Error in background rotation: {e}")
            logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")

        # Wait for rotation interval or stop event
        logger.debug(f"Waiting {IMAGE_ROTATION_INTERVAL} seconds for next rotation...")
        stop_event.wait(IMAGE_ROTATION_INTERVAL)

    logger.debug("Background rotation thread stopped")

def sighandler(signum, frame):
    """Signal handler for graceful shutdown"""
    logger.info("Received shutdown signal")
    stop_event.set()

def main():
    """Main demo function"""
    global current_background

    # Set up signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    if os.name == 'posix':
        signal.signal(signal.SIGQUIT, sighandler)

    try:
        # Initialize display
        logger.info("Initializing Turing Smart Screen Demo")
        initialize_display()

        # Create image manager
        image_manager = ImageManager(IMAGES_DIRECTORY,
                                   lcd_comm.get_width(),
                                   lcd_comm.get_height())

        # Get initial background
        current_background = image_manager.get_next_image()

        # Start background rotation thread
        bg_thread = Thread(target=background_rotation_thread,
                          args=(image_manager,),
                          daemon=True)
        bg_thread.start()

        # Main display loop
        frame_count = 0
        logger.info("Starting demo loop (Press Ctrl+C to exit)")
        logger.debug(f"Display dimensions: {lcd_comm.get_width()}x{lcd_comm.get_height()}")
        logger.debug(f"Current background: {current_background}")

        while not stop_event.is_set():
            start_time = time.perf_counter()

            try:
                logger.debug(f"Processing frame {frame_count}")

                # Check if we need to force refresh (new background)
                force_refresh = (frame_count == 0 or last_background != current_background)

                # Display demo content (only refreshes background when changed)
                display_demo_content(current_background, force_refresh)

                # Display animated progress bars (throttled updates)
                display_progress_bars(current_background, frame_count, force_refresh)

                frame_count += 1

                # Performance monitoring
                end_time = time.perf_counter()
                refresh_time = end_time - start_time

                if frame_count % 60 == 0:  # Log every 60 frames (less frequent)
                    logger.debug(f"Frame {frame_count}, refresh time: {refresh_time:.3f}s")
                    logger.debug(f"Average FPS: {1/refresh_time:.1f}")

                # Adaptive delay based on refresh time
                target_fps = 10  # Target 10 FPS to reduce flicker
                target_time = 1.0 / target_fps
                sleep_time = max(0, target_time - refresh_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.debug(f"Frame {frame_count} failed - Exception details: {type(e).__name__}: {str(e)}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)  # Wait before retrying

        logger.info("Demo stopped")

    except Exception as e:
        logger.error(f"Fatal error: {e}")

    finally:
        # Clean shutdown
        if lcd_comm:
            try:
                lcd_comm.closeSerial()
                logger.info("LCD connection closed")
            except:
                pass

if __name__ == "__main__":
    main()
