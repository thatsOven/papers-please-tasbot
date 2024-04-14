import logging

logger = logging.getLogger('tas.' + __name__)

try:
    from modules.textRecognition.textRecognition import *
    logger.info("using Cython compiled text recognition")
except ImportError:
    from modules.textRecognition.source.textRecognition import *
    logger.info("using Python text recognition")