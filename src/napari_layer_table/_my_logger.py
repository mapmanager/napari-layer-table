import logging

# log to console
logger = logging
level = logging.INFO
consoleFormat = '%(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s'
logger.basicConfig(format=consoleFormat, level=level)