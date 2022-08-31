# Configure logging format
import logging

logging.basicConfig(# format='%(asctime)s [%(levelname)s] %(message)s in %(pathname)s:%(lineno)d',
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[
                        # logging.FileHandler("log.log", mode='w'),  # Log in textfile (erased at each start)
                        logging.StreamHandler()  # Log also in console
                    ],
                    datefmt='%H:%M:%S')

logger = logging.getLogger('turing')
logger.setLevel(logging.DEBUG)  # Lowest log level : print all messages
