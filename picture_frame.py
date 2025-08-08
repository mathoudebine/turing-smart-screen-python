#!/usr/bin/env python3
# Simple Image Slideshow for Turing Smart Screen
# Based on turing-smart-screen-python library

"""
Turing Smart Screen Image Slideshow

Description:
This script displays an automated slideshow of images on a Turing Smart Screen display.
It supports both portrait and landscape images, automatically resizing and formatting them
to fit the display. Portrait images are displayed in pairs side-by-side.

Features:
- Automatic image rotation at configurable intervals
- Support for multiple display hardware revisions (A, B, C, D, SIMU)
- Time and date overlay on displayed images
- Recursive directory searching for images
- Automatic creation of default image if none found

Configuration:
1. Command Line Arguments:
   --debug       : Enable debug output (more verbose logging)
   --images PATH : Specify directory containing images (default: './images')
   --recursive   : Search for images recursively in subdirectories

2. Hardcoded Configuration (modify in code):
   - COM_PORT: Serial port for display ("AUTO" for auto-detection)
   - REVISION: Display hardware revision (A, B, C, D, or SIMU)
   - IMAGE_ROTATION_INTERVAL: Seconds between image changes (default: 30)
   - WIDTH, HEIGHT: Display dimensions in portrait mode (default: 320x480)

Usage:
1. Place images in the 'images' directory (or specify custom path with --images)
2. Run script: python3 picture_frame.py [options]
3. Press Ctrl+C to exit gracefully

Image Requirements:
- Supported formats: PNG, JPG/JPEG, BMP, GIF
- Any orientation (portrait or landscape)
- Will be automatically resized and formatted for display

Note:
To run picture_frame.py from any PATH environment folder (copied this script to run globally),
must copy library/ folder to /home/${USER}/.local/lib/python<version>/site-packages/
Creates a '.images' directory for processed versions of source images.
First run may be slow as it processes all images.
"""

import os
import signal
import sys
import time
import glob
import random
import argparse
import logging
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

# Verbosity configuration - will be set by command line args
VERBOSE_LEVEL = "INFO"  # Default to INFO level

def configure_logging(verbose_level):
    """Configure both custom and library logging levels"""
    # Configure the library's logger
    library_logger = logging.getLogger('library')

    if verbose_level == "DEBUG":
        library_logger.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    else:
        library_logger.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    # Also configure the root logger to be safe
    if verbose_level == "DEBUG":
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

def log_info(message):
    """Log info message if verbosity allows"""
    logger.info(message)

def log_debug(message):
    """Log debug message if verbosity allows"""
    if VERBOSE_LEVEL == "DEBUG":
        logger.debug(message)

def log_warning(message):
    """Log warning message (always shown)"""
    logger.warning(message)

def log_error(message):
    """Log error message (always shown)"""
    logger.error(message)

# Global variables
stop_event = Event()
lcd_comm = None
current_background = None
last_background = None

class ImageManager:
    """Handles image loading, resizing, and rotation with orientation detection"""

    def __init__(self, source_images_dir, recursive_search=False, display_width=320, display_height=480):
        self.source_images_dir = source_images_dir
        self.recursive_search = recursive_search
        self.display_width = display_width
        self.display_height = display_height

        # Create .images directory in current location for processed images
        self.processed_images_dir = ".images"
        if not os.path.exists(self.processed_images_dir):
            os.makedirs(self.processed_images_dir)
            log_info(f"Created processed images directory: {self.processed_images_dir}")

        self.image_list = []
        self.portrait_images = []
        self.landscape_images = []
        self.current_index = 0
        self.load_images()

    def load_images(self):
        """Scan directory for supported image files and categorize by orientation"""
        if not os.path.exists(self.source_images_dir):
            os.makedirs(self.source_images_dir)
            log_warning(f"Created source images directory: {self.source_images_dir}")
            log_info("Please add some images (PNG, JPG, JPEG, BMP, GIF) to the source images directory")
            return

        # Supported image extensions
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']

        log_info(f"Scanning for images in: {os.path.abspath(self.source_images_dir)}")
        log_info(f"Recursive search: {'enabled' if self.recursive_search else 'disabled'}")

        # Search for images
        for ext in extensions:
            if self.recursive_search:
                # Recursive search using ** pattern
                pattern = os.path.join(self.source_images_dir, "**", ext)
                self.image_list.extend(glob.glob(pattern, recursive=True))
                pattern_upper = os.path.join(self.source_images_dir, "**", ext.upper())
                self.image_list.extend(glob.glob(pattern_upper, recursive=True))
            else:
                # Non-recursive search (only direct files)
                pattern = os.path.join(self.source_images_dir, ext)
                self.image_list.extend(glob.glob(pattern))
                pattern_upper = os.path.join(self.source_images_dir, ext.upper())
                self.image_list.extend(glob.glob(pattern_upper))

        if not self.image_list:
            log_warning(f"No images found in {self.source_images_dir} directory")
            # Create a default image if none found
            self.create_default_image()
        else:
            log_info(f"Found {len(self.image_list)} images in {self.source_images_dir}")
            if self.recursive_search:
                # Show which subdirectories contain images
                subdirs = set()
                for img_path in self.image_list:
                    subdir = os.path.dirname(os.path.relpath(img_path, self.source_images_dir))
                    if subdir and subdir != '.':
                        subdirs.add(subdir)
                if subdirs:
                    log_info(f"Images found in subdirectories: {', '.join(sorted(subdirs))}")

            # Categorize images by orientation
            self.categorize_images_by_orientation()
            # Shuffle both lists for random order
            random.shuffle(self.portrait_images)
            random.shuffle(self.landscape_images)

    def categorize_images_by_orientation(self):
        """Categorize images into portrait and landscape lists"""
        self.portrait_images = []
        self.landscape_images = []

        for image_path in self.image_list:
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    if height > width:
                        self.portrait_images.append(image_path)
                        log_debug(f"Portrait: {os.path.basename(image_path)} ({width}x{height})")
                    else:
                        self.landscape_images.append(image_path)
                        log_debug(f"Landscape: {os.path.basename(image_path)} ({width}x{height})")
            except Exception as e:
                log_error(f"Error reading image {image_path}: {e}")
                continue

        log_info(f"Categorized images: {len(self.portrait_images)} portrait, {len(self.landscape_images)} landscape")

    def create_default_image(self):
        """Create a default gradient background if no images are found"""
        default_path = os.path.join(self.processed_images_dir, "default_background.png")

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
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Example path
        try:
            font = ImageFont.truetype(font_path, 40)
        except:
            font = ImageFont.load_default()

        text = "Image Slideshow"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.display_width - text_width) // 2
        y = (self.display_height - text_height) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        img.save(default_path)
        self.landscape_images = [default_path]  # Treat default as landscape
        log_info(f"Created default background: {default_path}")

    def resize_portrait_pair(self, image_path1, image_path2):
        """Resize two portrait images to fit side by side on screen"""
        try:
            log_debug(f"Processing portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")

            # Load both images
            with Image.open(image_path1) as img1, Image.open(image_path2) as img2:
                # Convert to RGB if necessary
                if img1.mode != 'RGB':
                    img1 = img1.convert('RGB')
                if img2.mode != 'RGB':
                    img2 = img2.convert('RGB')

                # Each image gets half the screen width
                target_width = self.display_width // 2
                target_height = self.display_height

                # Resize both images to fit in their half-screen space
                resized_img1 = self.resize_to_fit(img1, target_width, target_height)
                resized_img2 = self.resize_to_fit(img2, target_width, target_height)

                # Create final combined image
                final_img = Image.new('RGB', (self.display_width, self.display_height), (0, 0, 0))

                # Center each image in its half
                x1 = (target_width - resized_img1.width) // 2
                y1 = (target_height - resized_img1.height) // 2
                final_img.paste(resized_img1, (x1, y1))

                x2 = target_width + (target_width - resized_img2.width) // 2
                y2 = (target_height - resized_img2.height) // 2
                final_img.paste(resized_img2, (x2, y2))

                # Save processed image in .images directory
                base_name1 = os.path.splitext(os.path.basename(image_path1))[0]
                base_name2 = os.path.splitext(os.path.basename(image_path2))[0]
                processed_path = os.path.join(self.processed_images_dir, f"processed_pair_{base_name1}_{base_name2}.png")
                final_img.save(processed_path)

                log_info(f"Created portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")
                log_debug(f"Saved to: {processed_path}")

                return processed_path

        except Exception as e:
            log_error(f"Error processing portrait pair {image_path1}, {image_path2}: {e}")
            return None

    def resize_landscape_single(self, image_path):
        """Resize single landscape image to fill full screen (crop to fill, no black bars)"""
        try:
            log_debug(f"Processing landscape image: {os.path.basename(image_path)}")
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Use crop-to-fill approach to eliminate black bars
                final_img = self.resize_to_fill(img, self.display_width, self.display_height)

                # Save processed image in .images directory
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                processed_path = os.path.join(self.processed_images_dir, f"processed_landscape_{base_name}.png")
                final_img.save(processed_path)

                log_info(f"Processed landscape (crop-to-fill): {os.path.basename(image_path)}")
                log_debug(f"Saved to: {processed_path}")

                return processed_path

        except Exception as e:
            log_error(f"Error processing landscape image {image_path}: {e}")
            return None

    def resize_to_fit(self, img, target_width, target_height):
        """Helper method to resize image to fit within target dimensions while maintaining aspect ratio"""
        orig_width, orig_height = img.size

        # Calculate scaling factor to fit within bounds
        scale_x = target_width / orig_width
        scale_y = target_height / orig_height
        scale = min(scale_x, scale_y)  # Use smaller scale to fit entirely

        # Calculate new dimensions
        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)

        # Resize image
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def resize_to_fill(self, img, target_width, target_height):
        """Helper method to resize and crop image to fill target dimensions completely (no black bars)"""
        orig_width, orig_height = img.size

        # Calculate scaling factor to fill the entire target area
        scale_x = target_width / orig_width
        scale_y = target_height / orig_height
        scale = max(scale_x, scale_y)  # Use larger scale to fill entirely

        # Calculate new dimensions (will be larger than target)
        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)

        log_debug(f"Fill scaling: {orig_width}x{orig_height} -> {new_width}x{new_height} (scale: {scale:.3f})")

        # Resize image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate crop coordinates to center the image
        crop_x = (new_width - target_width) // 2
        crop_y = (new_height - target_height) // 2

        log_debug(f"Cropping from ({crop_x}, {crop_y}) to get {target_width}x{target_height}")

        # Crop to exact target dimensions
        cropped_img = resized_img.crop((crop_x, crop_y, crop_x + target_width, crop_y + target_height))

        return cropped_img

    def get_next_image(self):
        """Get the next processed image for display with 50/50 probability between portrait pairs and landscape"""
        if not self.portrait_images and not self.landscape_images:
            return None

        # Check what's available
        can_show_portrait_pair = len(self.portrait_images) >= 2
        can_show_landscape = len(self.landscape_images) > 0
        can_show_single_portrait = len(self.portrait_images) > 0

        # If both portrait pairs and landscape are available, randomly choose (50/50)
        if can_show_portrait_pair and can_show_landscape:
            show_portrait_pair = random.choice([True, False])
            log_debug(f"Random choice: {'Portrait pair' if show_portrait_pair else 'Landscape'}")

            if show_portrait_pair:
                return self._get_portrait_pair()
            else:
                return self._get_landscape_single()

        # If only portrait pairs are available
        elif can_show_portrait_pair:
            log_debug("Only portrait pairs available")
            return self._get_portrait_pair()

        # If only landscape images are available
        elif can_show_landscape:
            log_debug("Only landscape images available")
            return self._get_landscape_single()

        # If only single portrait images are left, treat as landscape
        elif can_show_single_portrait:
            log_debug("Only single portrait images left, treating as landscape")
            img = self.portrait_images.pop(0)
            self.portrait_images.append(img)
            return self.resize_landscape_single(img)

        return None

    def _get_portrait_pair(self):
        """Helper method to get a portrait pair"""
        # Get two random portrait images
        img1 = self.portrait_images.pop(0)
        img2 = self.portrait_images.pop(0)

        # Add them back to the end for rotation
        self.portrait_images.extend([img1, img2])

        return self.resize_portrait_pair(img1, img2)

    def _get_landscape_single(self):
        """Helper method to get a landscape image"""
        # Get one landscape image
        img = self.landscape_images.pop(0)

        # Add it back to the end for rotation
        self.landscape_images.append(img)

        return self.resize_landscape_single(img)

def initialize_display():
    """Initialize the LCD communication"""
    global lcd_comm

    # Build LcdComm object based on hardware revision
    if REVISION == "A":
        log_info("Selected Hardware Revision A (Turing Smart Screen 3.5\" & UsbPCMonitor 3.5\"/5\")")
        lcd_comm = LcdCommRevA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "B":
        log_info("Selected Hardware Revision B (XuanFang screen 3.5\" version B / flagship)")
        lcd_comm = LcdCommRevB(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "C":
        log_info("Selected Hardware Revision C (Turing Smart Screen 5\")")
        lcd_comm = LcdCommRevC(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "D":
        log_info("Selected Hardware Revision D (Kipye Qiye Smart Display 3.5\")")
        lcd_comm = LcdCommRevD(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "SIMU":
        log_info("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=WIDTH, display_height=HEIGHT)
    else:
        log_error("Unknown revision")
        sys.exit(1)

    # Initialize display
    lcd_comm.Reset()
    lcd_comm.InitializeComm()
    lcd_comm.SetBrightness(level=50)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))
    lcd_comm.SetOrientation(orientation=Orientation.LANDSCAPE)

def display_slideshow_content(background_image, force_background_refresh=False):
    """Display slideshow content with time and date"""
    global last_background

    if not background_image or not os.path.exists(background_image):
        logger.warning(f"Background image not found or invalid: {background_image}")
        return

    try:
        # Only refresh background if it changed or forced
        background_changed = last_background != background_image
        if background_changed or force_background_refresh:
            logger.info(f"Displaying background: {os.path.basename(background_image)}")
            start_bg = time.perf_counter()
            lcd_comm.DisplayBitmap(background_image)
            last_background = background_image
            end_bg = time.perf_counter()
            logger.debug(f"Background display took: {end_bg - start_bg:.3f}s")

        # Current time (updates every second) - bottom right corner
        current_time = datetime.now().strftime("%H:%M:%S")
        lcd_comm.DisplayText(current_time,
                           lcd_comm.get_width() - 120, lcd_comm.get_height() - 30,
                           font_size=20,
                           font_color=(255, 255, 255),
                           background_image=background_image)

        # Only redraw static content when background changes
        if background_changed or force_background_refresh:
            logger.debug("Redrawing static content due to background change")

            # Current date - bottom right corner, above time
            current_date = datetime.now().strftime("%Y-%m-%d")
            day_name = datetime.now().strftime("%A")

            lcd_comm.DisplayText(current_date,
                               lcd_comm.get_width() - 120, lcd_comm.get_height() - 55,
                               font_size=16,
                               font_color=(200, 200, 200),
                               background_image=background_image)

            # Day of week - bottom right corner, above date
            lcd_comm.DisplayText(day_name,
                               lcd_comm.get_width() - 120, lcd_comm.get_height() - 75,
                               font_size=14,
                               font_color=(180, 180, 180),
                               background_image=background_image)

        logger.debug("Slideshow content display completed successfully")

    except Exception as e:
        logger.error(f"Error displaying slideshow content: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")

def background_rotation_thread(image_manager):
    """Thread function for rotating background images"""
    global current_background

    log_debug("Background rotation thread started")

    while not stop_event.is_set():
        try:
            log_debug("Getting next background image...")
            new_background = image_manager.get_next_image()
            if new_background:
                current_background = new_background
                log_info(f"Switched to background: {os.path.basename(new_background)}")
                log_debug(f"Full path: {new_background}")
            else:
                log_warning("Failed to get next background image")
        except Exception as e:
            log_error(f"Error in background rotation: {e}")
            log_debug(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")

        # Wait for rotation interval or stop event
        log_debug(f"Waiting {IMAGE_ROTATION_INTERVAL} seconds for next rotation...")
        stop_event.wait(IMAGE_ROTATION_INTERVAL)

    log_debug("Background rotation thread stopped")

def sighandler(signum, frame):
    """Signal handler for graceful shutdown"""
    log_info("Received shutdown signal")
    stop_event.set()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Turing Smart Screen Image Slideshow")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output (default: INFO level only)")
    parser.add_argument("--images", type=str, default="images",
                       help="Path to images directory (default: 'images' in current location)")
    parser.add_argument("--recursive", action="store_true",
                       help="Search for images recursively in subdirectories")
    return parser.parse_args()

def main():
    """Main slideshow function"""
    global current_background, VERBOSE_LEVEL

    # Parse command line arguments
    args = parse_arguments()

    # Set verbosity level based on arguments
    if args.debug:
        VERBOSE_LEVEL = "DEBUG"
        log_info("Debug mode enabled - showing all messages")
    else:
        VERBOSE_LEVEL = "INFO"
        log_info("Info mode - showing info, warning, and error messages only")

    configure_logging(VERBOSE_LEVEL)

    # Set up signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    if os.name == 'posix':
        signal.signal(signal.SIGQUIT, sighandler)

    try:
        # Initialize display
        log_info("Initializing Turing Smart Screen Image Slideshow")
        initialize_display()

        # Create image manager with command line arguments
        image_manager = ImageManager(source_images_dir=args.images,
                                   recursive_search=args.recursive,
                                   display_width=lcd_comm.get_width(),
                                   display_height=lcd_comm.get_height())

        # Get initial background
        current_background = image_manager.get_next_image()

        # Start background rotation thread
        bg_thread = Thread(target=background_rotation_thread,
                          args=(image_manager,),
                          daemon=True)
        bg_thread.start()

        # Main display loop
        frame_count = 0
        log_info("Starting image slideshow (Press Ctrl+C to exit)")
        log_info(f"Display dimensions: {lcd_comm.get_width()}x{lcd_comm.get_height()}")
        log_info(f"Image rotation interval: {IMAGE_ROTATION_INTERVAL} seconds")
        log_info(f"Source directory: {os.path.abspath(args.images)}")
        log_info(f"Recursive search: {'enabled' if args.recursive else 'disabled'}")
        log_info(f"Total images: {len(image_manager.image_list)}")

        while not stop_event.is_set():
            start_time = time.perf_counter()

            try:
                # Check if we need to force refresh (new background)
                force_refresh = (frame_count == 0 or last_background != current_background)

                # Display slideshow content (only refreshes background when changed)
                display_slideshow_content(current_background, force_refresh)

                frame_count += 1

                # Performance monitoring (less frequent)
                end_time = time.perf_counter()
                refresh_time = end_time - start_time

                # Target refresh rate - very relaxed 1 FPS
                target_fps = 1  # 1 FPS - updates once per second
                target_time = 1.0 / target_fps
                sleep_time = max(0.8, target_time - refresh_time)  # Minimum 0.8s sleep
                time.sleep(sleep_time)

            except Exception as e:
                log_error(f"Error in main loop: {e}")
                log_debug(f"Frame {frame_count} failed - Exception details: {type(e).__name__}: {str(e)}")
                import traceback
                log_debug(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)  # Wait before retrying

        log_info("Image slideshow stopped")

    except Exception as e:
        log_error(f"Fatal error: {e}")
        log_debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        log_debug(f"Traceback: {traceback.format_exc()}")

    finally:
        # Clean shutdown
        if lcd_comm:
            try:
                lcd_comm.closeSerial()
                log_info("LCD connection closed")
            except:
                pass

if __name__ == "__main__":
    main()
