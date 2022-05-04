import logging
import sys

# default logging level
logging_level = logging.INFO

# This will create a custom logger with the name as the module name
logger = logging.getLogger(__name__)
logger.setLevel(logging_level)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging_level)
#formatter = logging.Formatter('%(asctime)s - %(levelname)7s - %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s')
#formatter = logging.Formatter('%(levelname)7s - %(filename)s %(className)s %(funcName)s() line:%(lineno)d -- %(message)s')
formatter = logging.Formatter('%(levelname)7s - %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
