import logging
import sys

# This will create a custom logger with the name as the module name
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)5s - %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
